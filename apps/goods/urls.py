from django.urls import include,re_path,path
from . import  views
app_name = 'goods'
urlpatterns = [
path('', views.index, name='index'), # 首页
]
