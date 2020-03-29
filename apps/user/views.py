from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.urls import reverse
from apps.user.models import User,Address
from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo,OrderGoods
from django.core.paginator import Paginator

import re
from django.views import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer #导入加密方式
from itsdangerous import SignatureExpired #导入异常
from django.conf import settings #引入密钥

from django.core.mail import send_mail #发邮件
from celery_tasks.tasks import send_register_active_email #发出celery任务

from django.contrib.auth import authenticate,login,logout #authenticate进行登陆验证 login已验证的用户想附加到当前会话(session)中
from django.contrib.auth.mixins import LoginRequiredMixin


from django_redis import get_redis_connection #django-redis 提供了方法建立新的原生连接


# Create your views here.
def register(request):
    '''传统注册'''
    if request.method == 'get':
        return render(request,'register.html')
    else:
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验，是否都传了
        if not all([username, password, email]):
            # 数据不完整，返回注册页面，并提示错误
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        # 校验是否点击协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在user=None
            user = None
        # 用户名已存在
        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 进行用户注册AbstractUser中的方法 User.objects.create_user创建用户 但把激活项变成0
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 发送激活邮件，包括激活链接，http://127.0.0.1:8000/user/active/3
        # 激活链接中需要包含用户的身份信息，并且把身份信息加密

        #加密用户身份信息,生成激活的token口令信息
        serializer=Serializer(settings.SECRET_KEY,3600)
        info={'confirm':user.id}
        token=serializer.dumps(info)

        #发邮件



        # 返回应答，跳转到首页用反向解析redirect(reverse('index'))
        return redirect(reverse('goods:index'))

class RegisterView(View):
    '''类视图进行注册'''
    def get(self,request):
        return render(request, 'register.html')
    def post(self,request):
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验，是否都传了
        if not all([username, password, email]):
            # 数据不完整，返回注册页面，并提示错误
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        # 校验是否点击协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在user=None
            user = None
        # 用户名已存在
        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 进行用户注册AbstractUser中的方法 User.objects.create_user创建用户 但把激活项变成0
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        #发送激活邮件，包括激活链接，http://127.0.0.1:8000/user/active/3
        #激活链接中需要包含用户的身份信息，并且把身份信息加密
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)  #bytes字节流 需转化为字符串
        token=token.decode()  #decode解码


        #发邮件
        send_register_active_email.delay(email,username,token)#用delay 放在任务队列

        # 返回应答，跳转到首页用反向解析redirect(reverse('index'))
        return redirect(reverse('goods:index'))

class ActiveView(View):
    '''激活'''
    def get(self,request,token):
        #进行解密,获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info=serializer.loads(token)
            #获取待激活用户的id
            user_id=info['confirm']
            #根据id获取用户信息
            user=User.objects.get(id=user_id)
            user.is_active=1
            user.save()

            #跳转到登陆页面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            #激活链接已过期
            return HttpResponse('激活链接已过期')

#/user/login/
class LoginView(View):
    '''登陆'''
    def get(self,request):
        '''显示登陆页面'''
        if 'username' in request.COOKIES:
            username=request.COOKIES.get('username')
            checked='checked'
        else:
            username=''
            checked = ''
        return render(request,'login.html',{'username':username,'checked':checked})
    def post(self,request):
        '''登陆校验'''
        #接收数据
        username=request.POST.get('username')
        password=request.POST.get('pwd')

        #校验数据
        if not all([username,password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        #业务处理：登陆校验
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                #用户激活，记录用户状态
                login(request, user)

                # 默认跳转到跳转到首页，
                next_url=request.GET.get('next',reverse('goods:index'))

                #跳转到next_url
                response=redirect(next_url)

                #判断是否需要记住用户名
                remember = request.POST.get('remember')
                if remember == 'on':
                    #记住用户名
                    response.set_cookie('username',username,max_age=7*24*3600)
                else:
                    response.delete_cookie('username')
                return response

            else:
                return render(request,'login.html',{'errmsg':'账户未激活'})
        else:
            return render(request,'login.html',{'errmsg':'用户名或密码错误'})

#/user/logout/
class LogoutView(View):
    '''退出登陆'''
    def get(self,request):
        #清楚session信息
        logout(request)

        #跳转到首页
        return redirect(reverse('goods:index'))

#/user
class UserInfoView(LoginRequiredMixin,View):#使用LoginRequiredMixin 如果未登陆进去会跳转至settings中的LOGIN_URL，并保存请求的路径在？next=中
    '''用户中心-信息页'''
    def get(self,request):
        #django本身会给request对象添加一个属性request.user
        #如果用户登陆 user是User类的实例，下面的方法返回ture，
        #如果未登陆，user是AnonymousUser类的一个实例，方法返回false
        #request.user.is_authenticated
        #除了给模版文件传递的变量{}以外，django框架会把request.user也传给模板文件

        #获取用户的个人信息
        user=request.user
        address = Address.objects.get_default_address(user)

        #获取用户的历史浏览记录
        #链接数据库
        #from redis import Redis  # 将用户浏览记录存于redis缓存中
        #sr=Redis(host='localhost', port=6379, decode_responses=True,db=9)

        con = get_redis_connection("default") #con是一个实例对象<redis.client.StrictRedis object at 0x2dc4510>

        history_key='history_%d'%user.id
        #获取用户最新浏览的商品的id
        sku_ids=con.lrange(history_key,0,4)

        #从数据库中查询用户浏览的5个商品的具体信息
        goods_li=GoodsSKU.objects.filter(id__in=sku_ids)

        # #遍历获取
        # goods_res=[]
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)
        # 遍历获取用户浏览的商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        #组织上下文
        context={'page':'user','address':address,'goods_li':goods_li}
        return render(request,'user_center_info.html',context)

#/user/order/1
class UserOrderView(LoginRequiredMixin,View):
    '''用户中心-订单页'''
    def get(self,request,page):
        #获取用户的订单信息
        user=request.user
        orders=OrderInfo.objects.filter(user=user).order_by('-create_time') #新提交的在前面

        #遍历获取订单商品的信息
        for order in orders:
            order_skus=OrderGoods.objects.filter(order_id=order.order_id)

            #遍历order_skus计算商品小计
            for order_sku in order_skus:
                #计算小计:
                amount=order_sku.count*order_sku.price
                #动态给order_sku增加amount属性，保存订单商品的小计
                order_sku.amount= amount

            #动态给order增加属性,保存订单状态的标题
            order.status_name=OrderInfo.ORDER_STATUS[order.order_status]
            #动态给order增加属性，保存订单商品的信息
            order.order_skus=order_skus


        #分页
        paginator=Paginator(orders,1)

        #处理页码

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        order_page = paginator.page(page)
        # 进行页码的控制
        num_pages = paginator.num_pages
        # 1、小于5显示全部
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        # 当前页是前三页，显示1-5
        elif page <= 3:
            pages = range(1, 6)
        # 当前页是最后三页，显示最后5页
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page - 3)

        #组织上下文
        context={'order_page':order_page,
                 'pages':pages,
                 'page': 'order'
                 }

        #使用模板
        return render(request,'user_center_order.html',context)

#/user/address
class AddressView(LoginRequiredMixin,View):
    '''用户中心-地址页'''
    def get(self,request):
        #获取用户的默认收货地址
        #获取登陆用户的User对象
        user = request.user

        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认收货地址
        #     address = None
        #通过模型管理器类创建封装的方法
        address = Address.objects.get_default_address(user)
        #使用模板
        return render(request,'user_center_site.html',{'page':'address','address':address})
    def post(self,request):
        # 接受数据
        receiver=request.POST.get('receiver')
        addr=request.POST.get('addr')
        zip_code=request.POST.get('zip_code')
        phone=request.POST.get('phone')

        # 校验数据
        if not all([receiver,addr,phone]):
            return render(request,'user_center_site.html',{'errmsg':'数据不完整'})
        if not re.match(r'^1(3|4|5|6|7|8|9)\d{9}$',phone):
            return render(request,'user_center_site.html',{'errmsg':'手机格式不正确'})
        # 业务处理：地址添加
        #如果用户已存在默认收货地址，添加地址不为默认地址，否则未默认地址
        #获取登陆用户的User对象
        user=request.user

        # try:
        #     address=Address.objects.get(user=user,is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认收货地址
        #     address=None
        address=Address.objects.get_default_address(user)

        if address:#查到添加的新用户有默认地址，故新增的该地址不为默认，is_default=False
            is_default= False
        else:
            is_default= True

        #添加地址
        Address.objects.create(user=user,receiver=receiver,addr=addr,zip_code=zip_code,phone=phone,is_default=is_default)
        print('添加地址')
        # 返回应答
        return redirect(reverse('user:address'))









