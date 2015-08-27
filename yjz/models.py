#-*- coding:utf-8 -*-
from django.db import models

# Create your models here.


class User(models.Model):
    user = models.CharField(max_length=200, primary_key=True)
    pwd = models.CharField(max_length=100)


class PayBooks(models.Model):
    user = models.ForeignKey(User)
    money = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.SmallIntegerField(max_length=20)
    year = models.CharField(max_length=5)
    remark = models.CharField(max_length=300)
    stamp = models.CharField(max_length=50)


class Feedback(models.Model):
    user = models.ForeignKey(User)
    feed_back = models.CharField(max_length=300)
    feedBack_date = models.DateField()
