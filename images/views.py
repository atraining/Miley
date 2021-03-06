from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from .forms import ImageCreateForm
from .models import Image
from activities.utils import create_activity
from common.decorators import ajax_required
import redis
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

rdis = redis.StrictRedis(host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DATABASE)

@login_required
def image_create(request):
    if request.method == 'POST':
        form = ImageCreateForm(data=request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            new_item = form.save(commit=False)
            new_item.user = request.user
            new_item.save()
            messages.success(request, 'Image added successfully')
            return redirect(new_item.get_absolute_url())
    else:
        form = ImageCreateForm(data=request.GET)

    return render(request, 'images/image/create.html', {'section': 'images',
        'form': form})

def image_detail(request, id, slug):
    image = get_object_or_404(Image, id=id, slug=slug)
    total_views = rdis.incr('image:{}:views'.format(image.id))
    rdis.zincrby('image_ranking', image.id, 1)
    return render(request, 'images/image/detail.html', {'section': 'images',
        'image': image,
        'total_views': total_views})

@login_required
def image_list(request):
    images = Image.objects.filter(user=request.user)
    paginator = Paginator(images, 8)
    page = request.GET.get('page')
    try:
        images = paginator.page(page)
    except PageNotAnInteger:
        images = paginator.page(1)
    except EmptyPage:
        if request.is_ajax():
            return HttpResponse('')
        images = paginator.page(paginator.num_pages)
    if request.is_ajax():
        return render(request,
            'images/list_ajax.html',
            {'section': 'images',
            'images': images})
    return render(request, 'images/list.html', {'section': 'images',
        'images': images})

# @ajax_required
@login_required
@require_POST
def image_like(request):
    json_data = json.loads(request.body)
    image_id = json_data['id']
    action = json_data['action']
    if image_id and action:
        try:
            image = Image.objects.get(id=image_id)
            if action == 'like':
                image.users_like.add(request.user)
            else:
                image.users_like.remove(request.user)
            return JsonResponse({'status': 'ok'})
        except:
            pass
    return JsonResponse({'status': 'ok'})

@login_required
def image_ranking(request):
    image_ranking = rdis.zrange('image_ranking', 0, -1, desc=True)
    image_ranking_ids = [int(id) for id in image_ranking[:10]]
    most_viewed = list(Image.objects.filter(id__in=image_ranking_ids))
    most_viewed.sort(key=lambda x: image_ranking_ids.index(x.id))
    return render(request, 'images/image/ranking.html', {'section': 'images',
        'most_viewed': most_viewed})
