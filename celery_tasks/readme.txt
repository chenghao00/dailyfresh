#启动Celery任务处理者的worker


’‘’第一步‘’‘
在dailyfresh下创建一个包celery_tasks

#使用celery
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail #发邮件
import time
import os
import django

#配置django的初始配置
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
django.setup()
#创建一个Celery类的实力对象 #添加中间人redis
app=Celery('celery_tasks.tasks',broker='redis://127.0.0.1:6379/8')

#定义任务函数
@app.task
def send_register_active_email(to_email,username,token):
    '''发送激活邮件h'''
    html_message = "<h1>%s,欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br><a href='http://127.0.0.1:8000/user/active/%s'>http://127.0.0.1:8000/user/active/%s</a>" % (username, token, token)
    send_mail(subject='天天生鲜欢迎信息', message='', from_email=settings.EMAIL_FROM, recipient_list=[to_email],html_message=html_message)



’‘’第二步‘’‘
from celery_tasks.tasks import send_register_active_email

send_register_active_email.delay(email,username,token)#用delay 放在任务队列



’‘’第三步‘’‘
#在dailyfresh目录下
启动worker
celery -A celery_tasks.tasks worker -l info