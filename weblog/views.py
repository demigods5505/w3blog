from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.http import Http404, HttpResponseRedirect
from django.conf import settings
from django.utils import translation
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from .apps import SETTINGS as blog_settings
from .models import BlogPost, Translation, PostComment, Category, CategoryTranslation, PostCommentForm
import datetime

#Why the hell didn't I just pass the variables to the context_dict in the first place??
#Need to remove this later
IS_MULTILINGUAL = blog_settings['multilingual']
BASE_TEMPLATE = blog_settings['base_template']
BLOG_TITLE = blog_settings['blog_title']
SHOW_SIDEBAR = blog_settings['show_sidebar']
POSTS_PER_PAGE = blog_settings['posts_per_page']
SHOW_AUTHOR = blog_settings['show_author']
USE_AUTHORS_USERNAME = blog_settings['use_authors_username']
ENABLE_COMMENTS = blog_settings['enable_comments']
ALLOW_ANON_COMMENTS = blog_settings['allow_anon_comments']

def Index(request, **kwargs):
    context_dict = blog_settings.copy()
    now = datetime.datetime.now()
    all_pages = BlogPost.objects.filter(published=True, publish_date__lte=now)
    category = None
    if kwargs is not None:
        category_slug = kwargs.get('category_slug')
        year = kwargs.get('year')
        month = kwargs.get('month')
    if category_slug:
        if category_slug == 'misc':
            all_pages = BlogPost.objects.filter(published=True, publish_date__lte=now, categories=None)
            context_dict['category'] = 'misc'
        else:
            category = get_object_or_404(Category, slug=category_slug)
            context_dict['category'] = category
            all_pages = BlogPost.objects.filter(published=True, publish_date__lte=now, categories__slug=category_slug)
    if year:
        all_pages = BlogPost.objects.filter(published=True, publish_date__lte=now, publish_date__year=year)
        if month:
            all_pages = BlogPost.objects.filter(published=True, publish_date__lte=now, publish_date__month=month)
    post_count = all_pages.count()
    if post_count < 1:
        return render(request, 'weblog/index.html', context_dict)
    page = 0
    if request.GET.get('page'):
        page = int(request.GET['page'])-1
    if page * POSTS_PER_PAGE + 1 > post_count:
        page = 0
    context_dict['current_page'] = page+1
    slice_start = page*POSTS_PER_PAGE
    slice_end = page*POSTS_PER_PAGE + POSTS_PER_PAGE
    if slice_end >= post_count:
        slice_end = post_count
    if post_count % POSTS_PER_PAGE == 0:
        last_page = int(post_count/POSTS_PER_PAGE)
    else:
        last_page = int(post_count/POSTS_PER_PAGE)+1
    context_dict['last_page'] = last_page
    posts_raw = all_pages[slice_start:slice_end]
    if category_slug:
        posts_raw = all_pages[slice_start:slice_end]
    current_language = translation.get_language()
    if current_language is None:
        current_language = settings.LANGUAGE_CODE
    if category_slug:
        if IS_MULTILINGUAL and category_slug != 'misc':
            category_translations = CategoryTranslation.objects.filter(category=category)
            if category_translations.count() > 0:
                for cat_trans in category_translations:
                    if current_language[0:2] == cat_trans.language[0:2]:
                        context_dict['category'] = cat_trans
        if category_slug == 'misc':
            context_dict['breadcrumbs'] = [{'url': reverse('weblog:CategoryIndex', kwargs={'category_slug': category_slug}), 'name': pgettext_lazy('Posts without category', 'Uncategorized')},]
        else:
            context_dict['breadcrumbs'] = [{'url': reverse('weblog:CategoryIndex', kwargs={'category_slug': category_slug}), 'name': context_dict['category']},]
    posts = []
    for post_raw in posts_raw:
        post = {'publish_date': post_raw.publish_date, 'url': post_raw.get_absolute_url()}
        if SHOW_AUTHOR:
            post['author'] = post_raw.author.get_full_name()
            if USE_AUTHORS_USERNAME:
                post['author'] = post_raw.author.get_username()
        translation_exists = False
        post_translations = Translation.objects.filter(post=post_raw)
        if post_translations.count() < 1 or not IS_MULTILINGUAL:
            post['title'] = post_raw.title
            post['content'] = post_raw.content
            post['preview_image'] = post_raw.preview_image
            if len(post_raw.preview_text) > 5:
                post['preview_text'] = post_raw.preview_text
            else:
                post['preview_text'] = post_raw.content.split('</p>', 1)[0]+'</p>'
        else:
            post_trans = None
            orig_lang = post_raw.original_language
            if len(orig_lang) < 2:
                orig_lang = settings.LANGUAGE_CODE[0:2]
            post['languages'] = [orig_lang,]
            for post_translation in post_translations:
                post['languages'].append(post_translation.language)
                if current_language[0:2] == post_translation.language[0:2]:
                    post_trans = post_translation
            if post_trans:
                post['title'] = post_trans.title
                post['content'] = post_trans.content
                post['current_language'] = post_trans.language
                post['preview_image'] = post_trans.preview_image
                if len(post_trans.preview_text) > 5:
                    post['preview_text'] = post_trans.preview_text
                else:
                    post['preview_text'] = post_trans.content.split('\n', 1)[0]+'</p>'
            else:
                post['title'] = post_raw.title
                post['content'] = post_raw.content
                post['current_language'] = orig_lang
                post['preview_image'] = post_raw.preview_image
                if len(post_raw.preview_text) > 5:
                    post['preview_text'] = post_raw.preview_text
                else:
                    post['preview_text'] = post_raw.content.split('</p>', 1)[0]+'</p>'
        posts.append(post)
    context_dict['posts'] = posts
    return render(request, 'weblog/index.html', context_dict)


def PostView(request, category_slug, post_slug):
    post = get_object_or_404(BlogPost, slug=post_slug)
    context_dict = blog_settings.copy()
    context_dict['comment_form'] = PostCommentForm()
    post_translations = Translation.objects.filter(post=post)
    category = None
    current_language = translation.get_language()
    if current_language is None:
        current_language = settings.LANGUAGE_CODE
    if category_slug:
        if category_slug == 'misc':
            context_dict['category'] = 'misc'
        else:
            category = get_object_or_404(Category, slug=category_slug)
            context_dict['category'] = category
            if IS_MULTILINGUAL:
                category_translations = CategoryTranslation.objects.filter(category=category)
                if category_translations.count() > 0:
                    for cat_trans in category_translations:
                        if current_language[0:2] == cat_trans.language[0:2]:
                            context_dict['category'] = cat_trans
        if category_slug == 'misc':
            context_dict['breadcrumbs'] = [{'url': reverse('weblog:CategoryIndex', kwargs={'category_slug': category_slug}), 'name': pgettext_lazy('Posts without category', 'Uncategorized')},]
        else:
            context_dict['breadcrumbs'] = [{'url': reverse('weblog:CategoryIndex', kwargs={'category_slug': category_slug}), 'name': context_dict['category']},]
    if SHOW_AUTHOR:
        context_dict['post_author'] = post.author.get_full_name()
        if USE_AUTHORS_USERNAME:
            context_dict['post_author'] = post.author.get_username()
    if ENABLE_COMMENTS:
        context_dict['comments'] = PostComment.objects.filter(post=post)
    if request.method == 'POST':
        form = PostCommentForm(request.POST)
        context_dict['comment_submission'] = True
        if form.is_valid():
            comment_content = form.cleaned_data['content']
            if request.user.is_authenticated():
                new_comment = PostComment(author=request.user, post=post, content=comment_content)
                new_comment.save()
            elif ALLOW_ANON_COMMENTS:
                new_comment = PostComment(post=post, content=comment_content)
                new_comment.save()    
            else:
                context_dict['comment_submission_error'] = _('You need to sign in to submit a comment')
        else:
            context_dict['comment_submission_error'] = _('Error submitting comment: Invalid data')
    context_dict['post'] = post
    if post.categories.all().count() > 0:
        context_dict['post_categories'] = []
        for raw_category in post.categories.all():
            next_category = {'name': raw_category.name, 'slug': raw_category.slug}
            if CategoryTranslation.objects.filter(category=raw_category).count() > 0 and IS_MULTILINGUAL:
                for category_translation in CategoryTranslation.objects.filter(category=raw_category):
                    if current_language[0:2] == category_translation.language[0:2]:
                        next_category['name'] = category_translation.name
            context_dict['post_categories'].append(next_category)
    if post_translations.count() < 1 or not IS_MULTILINGUAL:
        context_dict['breadcrumbs'].append({'url': post.get_absolute_url(), 'name': post.title})
        return render(request, 'weblog/post.html', context_dict)
    orig_lang = post.original_language
    if len(orig_lang) < 2:
        orig_lang = settings.LANGUAGE_CODE[0:2]
    context_dict['languages'] = [orig_lang,]
    for post_translation in post_translations:
        context_dict['languages'].append(post_translation.language)
        if current_language[0:2] == post_translation.language[0:2]:
            context_dict['post_translation'] = post_translation
    if 'post_translation' in context_dict:
        context_dict['breadcrumbs'].append({'url': post.get_absolute_url(), 'name': post_translation.title})    
    else:
        context_dict['breadcrumbs'].append({'url': post.get_absolute_url(), 'name': post.title})
    return render(request, 'weblog/post.html', context_dict)

def ChangeLanguage(request, language):
    translation.activate(language)
    request.session[translation.LANGUAGE_SESSION_KEY] = language
    if request.GET.get('next'):
        return HttpResponseRedirect(request.GET['next'])
    return HttpResponseRedirect(reverse('weblog:Index'))
    