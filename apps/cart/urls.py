from django.urls import include, re_path, path
from apps.cart.views import CartAddView, CartInfoView

app_name = 'cart'
urlpatterns = [
    path('add/', CartAddView.as_view(), name='add'),# 购物车记录添加
    path('', CartInfoView.as_view(), name='show'),  # 购物车页面显示
]
