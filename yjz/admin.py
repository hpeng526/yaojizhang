#-*- coding:utf-8 -*-
from django.contrib import admin
from models import User, Feedback

__author__ = 'hp'


admin.site.register(User)
admin.site.register(Feedback)