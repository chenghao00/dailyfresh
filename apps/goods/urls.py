from django.urls import include, re_path, path
from apps.goods.views import IndexView, DetailView,ListView

app_name = 'goods'
urlpatterns = [
    path('index/', IndexView.as_view(), name='index'),  # 首页
    re_path('goods/(?P<goods_id>\d+)/', DetailView.as_view(), name='detail'),  # 详细信息页
    re_path('list/(?P<type_id>\d+)/(?P<page>\d+)/', ListView.as_view(), name='list'),#列表页
]
