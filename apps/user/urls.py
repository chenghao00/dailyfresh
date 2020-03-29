from django.urls import include, re_path, path
from . import views
from apps.user.views import RegisterView, ActiveView, LoginView, UserInfoView, UserOrderView, AddressView, LogoutView
from django.contrib.auth.decorators import login_required  # 登陆认证，装饰器

app_name = 'user'
urlpatterns = [
    # path('register/', views.register, name='register'), # 通过method来判断显示用户注册并处理注册
    path('register/', RegisterView.as_view(), name='register'),
    re_path('active/(?P<token>.*)/', ActiveView.as_view(), name='active'),
    path('login/', LoginView.as_view(), name='login'),
    # path('', login_required(UserInfoView.as_view()), name='user'),  未使用Mixin
    path('', UserInfoView.as_view(), name='user'),  # 使用Mixin
    re_path('order/(?P<page>\d+)/', UserOrderView.as_view(), name='order'),
    path('address/', AddressView.as_view(), name='address'),
    path('logout/', LogoutView.as_view(), name='logout')

]
