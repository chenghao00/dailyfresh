from django.urls import include,re_path,path
from apps.goods.views import IndexView
app_name = 'goods'
urlpatterns = [
path('', IndexView.as_view(), name='index'), # 首页
]
