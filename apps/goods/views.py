from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from apps.goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner
from apps.order.models import OrderGoods
from django_redis import get_redis_connection  # django-redis 提供了方法建立新的原生连接

from django.core.paginator import Paginator

from django.core.cache import cache  # 设置页面缓存


# Create your views here.
class IndexView(View):
    '''首页'''

    def get(self, request):
        # 尝试从缓存中获取数据
        context = cache.get('index_page_data')
        if context is None:
            print('设置缓存')
            # 获取商品的种类信息
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')  # 升序

            # 获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            for type in types:  # GoodsType
                # 获取type种类首页分类商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                # 获取type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
                type.image_banners = image_banners
                type.title_banners = title_banners

            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners,
            }

            # 设置缓存
            # 设置缓存的时间 ,为了开发
            cache.set('index_page_data', context, 3600)

        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:  # 'bool' object is not callable故不能用is_authenticated()
            # 用户已登录
            conn = get_redis_connection("default")  # con是一个实例对象<redis.client.StrictRedis object at 0x2dc4510>
            cart_key = 'cart_%d' % user.id
            # 获取用户购物车里的商品数目
            cart_count = conn.hlen(cart_key)

        # 组织模版上下文
        context.update(cart_count=cart_count)
        # 使用模板
        return render(request, 'index.html', context)


# 传商品id /goods/商品id/
class DetailView(View):
    def get(self, request, goods_id):
        '''显示详情页'''
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:

            # 商品不存在
            return redirect(reverse('goods:index'))
        # 获取商品的分类信息
        types = GoodsType.objects.all()
        # 获取商品的评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取同一个SPU规格的其他商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:  # 'bool' object is not callable故不能用is_authenticated()
            # 用户已登录
            conn = get_redis_connection("default")  # con是一个实例对象<redis.client.StrictRedis object at 0x2dc4510>
            cart_key = 'cart_%d' % user.id
            # 获取用户购物车里的商品数目
            cart_count = conn.hlen(cart_key)

            # 添加用户的历史浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            conn.lrem(history_key, 0, goods_id)
            # 把goods_id从列表左侧插入
            conn.lpush(history_key, goods_id)
            # 只保存用户最新的5条
            conn.ltrim(history_key, 0, 4)

        # 组织模版上下文
        context = {'sku': sku, 'types': types,
                   'sku_orders': sku_orders,
                   'new_skus': new_skus,
                   'cart_count': cart_count,
                   'same_spu_skus': same_spu_skus,
                   }
        return render(request, 'detail.html', context)


# 种类id，页码，排序方式
# restful api -> 访问地址 即是请求资源 在flask中常用
# /list/种类id/页码？sort=排序方式
class ListView(View):
    '''列表页'''

    def get(self, request, type_id, page):
        '''显示列表'''
        # 先获取种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 种类不存在
            return redirect(reverse('goods:index'))
        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 获取排序的方式 # 获取商品的分类信息
        # sort=default 按照默认id排序
        # sort=price 按照商品价格排序
        # sort=hot  按照商品的销量排序
        sort = request.GET.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        # 对数据进行分页
        paginator = Paginator(skus, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        skus_page = paginator.page(page)

        #进行页码的控制
        num_pages=paginator.num_pages
        # 1、小于5显示全部
        if num_pages<5:
            pages=range(1,num_pages+1)
        #当前页是前三页，显示1-5
        elif page <=3:
            pages=range(1,6)
        # 当前页是最后三页，显示最后5页
        elif num_pages - page <=2:
            pages=range(num_pages-4,num_pages+1)
        else:
            pages=range(page-2,page-3)



        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:  # 'bool' object is not callable故不能用is_authenticated()
            # 用户已登录
            conn = get_redis_connection("default")  # con是一个实例对象<redis.client.StrictRedis object at 0x2dc4510>
            cart_key = 'cart_%d' % user.id
            # 获取用户购物车里的商品数目
            cart_count = conn.hlen(cart_key)

        # 组织上下文
        context = {
            'type': type,
            'types': types,
            'skus_page': skus_page,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'pages':pages,
            'sort': sort,
        }
        return render(request, 'list.html', context)
