from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)
from django.utils import timezone

from .forms import (
    CommentForm,
    PostForm,
    ProfileForm,
    RegistrationForm
)
from .models import Category, Comment, Post

User = get_user_model()

POSTS_PER_PAGE = 10


def get_published_posts():
    return Post.objects.select_related(
        'category',
        'location',
        'author'
    ).annotate(
        comment_count=Count('comments')
    ).filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True
    )


def index(request):
    post_list = get_published_posts().order_by('-pub_date')

    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'blog/index.html',
        {'page_obj': page_obj}
    )


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = get_published_posts().filter(
        category=category
    ).order_by('-pub_date')

    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'blog/category.html',
        {
            'category': category,
            'page_obj': page_obj,
        }
    )


def post_detail(request, id):
    post = get_object_or_404(
        Post.objects.select_related(
            'category',
            'location',
            'author'
        ),
        pk=id
    )

    # Автор видит свою публикацию даже до даты публикации
    # и после снятия её с публикации администратором.
    if post.author != request.user:
        if (
                not post.is_published
                or post.pub_date > timezone.now()
                or not post.category.is_published
        ):
            from django.http import Http404
            raise Http404

    comments = post.comments.select_related(
        'author'
    ).all()

    return render(
        request,
        'blog/detail.html',
        {
            'post': post,
            'comments': comments,
            'form': CommentForm(),
        }
    )


def profile(request, username):
    profile_user = get_object_or_404(
        User,
        username=username
    )

    if request.user == profile_user:
        post_list = Post.objects.filter(
            author=profile_user
        )
    else:
        post_list = get_published_posts().filter(
            author=profile_user
        )

    post_list = post_list.select_related(
        'category',
        'location',
        'author'
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')

    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'blog/profile.html',
        {
            'profile': profile_user,
            'page_obj': page_obj,
        }
    )


def registration(request):
    form = RegistrationForm(
        request.POST or None
    )

    if form.is_valid():
        form.save()
        return redirect('login')

    return render(
        request,
        'registration/registration_form.html',
        {'form': form}
    )


@login_required
def edit_profile(request):
    form = ProfileForm(
        request.POST or None,
        instance=request.user
    )

    if form.is_valid():
        form.save()
        return redirect(
            'blog:profile',
            username=request.user.username
        )

    return render(
        request,
        'blog/user.html',
        {'form': form}
    )


@login_required
def create_post(request):
    form = PostForm(
        request.POST or None,
        request.FILES or None
    )

    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()

        return redirect(
            'blog:profile',
            username=request.user.username
        )

    return render(
        request,
        'blog/create.html',
        {'form': form}
    )


@login_required
def edit_post(request, id):
    post = get_object_or_404(Post, pk=id)

    if post.author != request.user:
        return redirect(
            'blog:post_detail',
            id=post.id
        )

    form = PostForm(
        request.POST or None,
        request.FILES or None,
        instance=post
    )

    if form.is_valid():
        form.save()
        return redirect(
            'blog:post_detail',
            id=post.id
        )

    return render(
        request,
        'blog/create.html',
        {'form': form}
    )


@login_required
def delete_post(request, id):
    post = get_object_or_404(Post, pk=id)

    if post.author != request.user:
        return redirect(
            'blog:post_detail',
            id=post.id
        )

    form = PostForm(instance=post)

    if request.method == 'POST':
        post.delete()
        return redirect(
            'blog:profile',
            username=request.user.username
        )

    return render(
        request,
        'blog/create.html',
        {'form': form}
    )


@login_required
def add_comment(request, id):
    post = get_object_or_404(
        get_published_posts(),
        pk=id
    )

    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()

    return redirect(
        'blog:post_detail',
        id=post.id
    )


@login_required
def edit_comment(request, id, comment_id):
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=id
    )

    if comment.author != request.user:
        return redirect(
            'blog:post_detail',
            id=id
        )

    form = CommentForm(
        request.POST or None,
        instance=comment
    )

    if form.is_valid():
        form.save()
        return redirect(
            'blog:post_detail',
            id=id
        )

    return render(
        request,
        'blog/comment.html',
        {
            'comment': comment,
            'form': form,
        }
    )


@login_required
def delete_comment(request, id, comment_id):
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=id
    )

    if comment.author != request.user:
        return redirect(
            'blog:post_detail',
            id=id
        )

    if request.method == 'POST':
        comment.delete()
        return redirect(
            'blog:post_detail',
            id=id
        )

    return render(
        request,
        'blog/comment.html',
        {'comment': comment}
    )
