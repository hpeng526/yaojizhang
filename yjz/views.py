#-*- coding:utf-8 -*-
import codecs
import csv
import hashlib
import time
import xml.etree.ElementTree as ET
from django.db.models import Sum
from django.shortcuts import render_to_response
from models import User, PayBooks, Feedback

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_str
from decimal import *
import datetime

import pylibmc


TOKEN = "xxx"
#ini memory cache

mc = pylibmc.Client()


@csrf_exempt
def handle_request(request):
    print('request: ' + request.method)
    if request.method == 'GET':
        response = HttpResponse(check_signature(request), content_type="text/plain")
        return response
    elif request.method == 'POST':
        response = HttpResponse(response_msg(request), content_type="application/xml")
        return response
    else:
        return None


def check_signature(request):
    token = TOKEN
    signature = request.GET.get("signature", None)
    timestamp = request.GET.get("timestamp", None)
    nonce = request.GET.get("nonce", None)
    echostr = request.GET.get("echostr", None)

    print('signature : %s, timestamp : %s, nonce : %s, echostr : %s' % (signature, timestamp, nonce, echostr))
    tmp_arr = [token, timestamp, nonce]
    tmp_arr.sort()
    tmp_str = ''.join(tmp_arr)
    code = hashlib.sha1(tmp_str).hexdigest()
    if code == signature:
        return echostr
    else:
        return None


def get_reply_xml(from_name, to_name, contents):
    reply = "<xml><ToUserName><![CDATA[%s]]></ToUserName><FromUserName><![CDATA[%s]]></FromUserName><CreateTime>%d</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[%s]]></Content><FuncFlag>0</FuncFlag></xml>" % (
        from_name, to_name, int(time.time()), contents)
    return reply


def parse_xml(root):
    msg = {}
    if root.tag == 'xml':
        for elem in root:
            msg[elem.tag] = smart_str(elem.text)
    return msg


def response_msg(request):
    raw_str = smart_str(request.raw_post_data)
    print raw_str
    msg = parse_xml(ET.fromstring(raw_str))
    msg_type = msg.get('MsgType', '')
    from_user_name = msg.get('FromUserName')
    to_user_name = msg.get('ToUserName')
    content = ''
    print('MsgType ' + msg_type)

    if msg_type == 'event':
        event_type = msg.get('Event', '')
        print('new event: ' + event_type)
        if event_type == 'subscribe':
            content = '欢迎关注要记账\n1.创建账本\n2.增加记录\n3.查询\n4.导出账单\n5.帮助\n6.删除账号并清空数据\n7.反馈'
            return get_reply_xml(from_user_name, to_user_name, content)
    elif msg_type == 'text':
        content = msg.get('Content', '')
        print('content: ' + content)
        if mc.get(from_user_name + 'del') == '22':
            if content == 'c' or content == 'C':
                record_stamp = mc.get(from_user_name + 'ds')
                u1 = User.objects.get(user=from_user_name)
                pb = PayBooks.objects.filter(user=u1, stamp=record_stamp)
                pb[0].delete()
                content = '撤销成功'
                return get_reply_xml(from_user_name, to_user_name, content)
                # if op_sql.revoke_insert(from_user_name):
                #     content = '撤销成功'
                # else:
                #     content = '撤销失败'
                # mc.delete(from_user_name + 'del')
                # return reply_server(from_user_name, to_user_name, content)

        if mc.get(from_user_name) == '1':
            print(mc.get(from_user_name) + ' name')
            u1 = User.objects.filter(user=from_user_name)
            if len(u1) == 0:
                print('create user but not exist')
                u1 = User(user=from_user_name, pwd=content)
                u1.save()
                content = '创建成功,此密码可以用来提取账单,如果你不幸忘记密码,请在反馈中联系[要记账]'
                mc.delete(from_user_name)
            else:
                print('create user failed exist')
                content = '创建失败,用户已经创建过密码'
                mc.delete(from_user_name)
            return get_reply_xml(from_user_name, to_user_name, content)

            # if op_sql.create(from_user_name, content):
            #     content = '创建成功,此密码未来可以提取账单到电脑'
            #     logging.debug(content + ' enter if op_sql')
            #     mc.delete(from_user_name)
            # else:
            #     content = '创建失败,用户已经创建过密码'
            #     mc.delete(from_user_name)
        elif mc.get(from_user_name) == '2':
            print(mc.get(from_user_name) + ' enter 2 content' + content)
            #logging.debug('show content : ' + content)
            tmp = content.split(' ')
            if not is_number(tmp[0]):
                content = '输入有误\n!格式不正确\n!金额不能为负数\n!用空格分隔\n请重新输入'
                return get_reply_xml(from_user_name, to_user_name, content)

            if len(tmp) == 2 and float(tmp[0]) > 0:
                user_tmp = User.objects.filter(user=from_user_name)
                if len(user_tmp) != 0:
                    record_time = time.strftime('%m%d%H%M%S')
                    pb = PayBooks(user=user_tmp[0],
                                  money=tmp[0],
                                  month=time.strftime('%m'),
                                  year=time.strftime('%Y'),
                                  remark=tmp[1],
                                  stamp=record_time
                    )
                    pb.save()
                    content = '数据记录成功\n在3分钟内回复c\n可以撤销刚才数据'
                    mc.delete(from_user_name)
                    mc.set(from_user_name + 'ds', record_time, 300)
                    # if user want to revoke the previous opration
                    mc.set(from_user_name + 'del', '22', 180)
                else:
                    print('insert error money format')
                    content = '数据记录失败,格式不对吧?还是没创建账户?'
                    mc.delete(from_user_name)
                    # if op_sql.insert(from_user_name, tmp[0], tmp[1]):
                    #     logging.debug('insert enter')
                    #     content = '数据记录成功\n在3分钟内回复c\n可以撤销刚才数据'
                    #     mc.delete(from_user_name)
                    #     # if user want to revoke the previous opration
                    #     mc.set(from_user_name + 'del', '22', 180)
                    # else:
                    #     logging.debug('insert error money')
                    #     content = '数据记录失败,格式不对吧?还是没创建账户?'
                    #     mc.delete(from_user_name)
            else:
                content = '输入有误\n!格式不正确\n!金额不能为负数\n!用空格分隔\n请重新输入'
            return get_reply_xml(from_user_name, to_user_name, content)
        elif mc.get(from_user_name) == '3':
            '''高级查询
            1         单参数,当前年月份
            12 2014   指定月份与年份,第二个数字大于3位数
            1 2       区间查询两个数字都是2位数,当前年
            2 5 2013 2014    4参数,指定区间月份年
            '''
            print('enter search')
            arg = content.split(" ")
            check = True
            u1 = User.objects.get(user=from_user_name)
            current_year = time.strftime('%Y')
            result = ''
            for c in arg:
                check = check and c.isdigit()

            if check:
                if len(arg) <= 2 and len(arg) != 0:
                    if len(arg) == 2:
                        if int(arg[1]) > 1000:
                            current_year = arg[1]
                        else:
                            m1 = arg[0]
                            m2 = arg[1]
                            if int(arg[0]) > int(arg[1]):
                                m1 = arg[1]
                                m2 = arg[0]
                            pb = PayBooks.objects.filter(user=u1, month__gte=m1, month__lte=m2, year=current_year)
                            result = current_year + "年\n" + "月列表: \n月份\t\t总额\n"
                            for i in range(int(m1), int(m2) + 1):
                                result += str(i) + '\t\t' + "{}".format(
                                    pb.filter(month=i).aggregate(Sum('money')).values()[0]) + "\n"
                            result += "总计: " + "{}".format(pb.aggregate(Sum('money')).values()[0])
                            content = "查询结果: \n" + result
                            mc.delete(from_user_name)
                            return get_reply_xml(from_user_name, to_user_name, content)

                    pb = PayBooks.objects.filter(user=u1, month=int(arg[0]), year=current_year)
                    result = current_year + "年\n" + arg[0] + "月列表: \n日期\t金额\t备注\n"
                    sum_money = Decimal("0.00")
                    for p in pb:
                        day = p.stamp
                        result += "{}".format(day[2]+day[3]) + "\t\t" + "{}".format(p.money) + "\t" \
                                  + "{}".format(p.remark.encode('utf8')) + "\n"
                        sum_money += p.money
                    result += "总计： " + "{}".format(sum_money)
                    content = "查询结果: \n" + result
                    mc.delete(from_user_name)
                    return get_reply_xml(from_user_name, to_user_name, content)
                elif len(arg) == 4:
                    m1 = arg[0]
                    m2 = arg[1]
                    y1 = arg[2]
                    y2 = arg[3]
                    if int(arg[2]) > int(arg[3]):
                        m1 = arg[1]
                        m2 = arg[0]
                        y1 = arg[3]
                        y2 = arg[2]
                    pb = PayBooks.objects.filter(user=u1, year__gte=y1, year__lte=y2)
                    sum_total = Decimal('0.00')
                    if y1 != y2:
                        sum_start = pb.filter(month__gte=m1, year=y1).aggregate(Sum('money')).values()[0]
                        sum_end = pb.filter(month__lte=m2, year=y2).aggregate(Sum('money')).values()[0]
                        for i in range(int(y1) + 1, int(y2)):
                            sum_temp = pb.filter(year=i).aggregate(Sum('money')).values()[0]
                            if sum_temp is not None:
                                sum_total += sum_temp
                        if sum_start is not None:
                            sum_total += sum_start
                        if sum_end is not None:
                            sum_total += sum_start
                    else:
                        sum_total = pb.aggregate(Sum('money')).values()[0]
                    result = y1 + '年 ' + m1 + '月到 ' + y2 + '年 ' + m2 + '月\n'
                    result += "总计: " + "{}".format(sum_total)
                    content = "查询结果: \n" + result
                    mc.delete(from_user_name)
                    return get_reply_xml(from_user_name, to_user_name, content)
                else:
                    content = '输入格式错误'
            else:
                content = '输入格式错误'
            return get_reply_xml(from_user_name, to_user_name, content)
        elif mc.get(from_user_name) == '4':
            content = '建设中'
            mc.delete(from_user_name)
            return get_reply_xml(from_user_name, to_user_name, content)
            # logging.debug('enter 4')
            # if content.isdigit():
            #     result = op_sql.search(from_user_name, content)
            # else:
            #     content = '输入有误\n请重新输入'
            #     return reply_server(from_user_name, to_user_name, content)
            # re = content + "月列表: \n金额\t\t备注"
            # result = op_sql.show_month_list(from_user_name, content)
            # re += result
            # mc.delete(from_user_name)
            # return reply_server(from_user_name, to_user_name, re)
        elif mc.get(from_user_name) == '6':
            print('enter delete 6')
            if content == 'Y' or content == 'y':
                u1 = User.objects.filter(user=from_user_name)
                u1.delete()
                content = '删除成功\n你为节省我的空间出了一份力,谢谢~'
            else:
                content = '操作无效'
            mc.delete(from_user_name)
            return get_reply_xml(from_user_name, to_user_name, content)
        elif mc.get(from_user_name) == '7':
            print('enter 7')
            u1 = User.objects.get(user=from_user_name)
            fb = Feedback(user=u1, feed_back=unicode(content, 'utf8'), feedBack_date=datetime.date.today())
            fb.save()
            content = '谢谢您的反馈,我会及时跟进滴'
            mc.delete(from_user_name)
            return get_reply_xml(from_user_name, to_user_name, content)
        if content == '1':
            content = '请设置您的初始密码'
            mc.set(from_user_name, '1', 180)
        elif content == '2':
            content = '插入数据格式为 金额 备注 \n 例如: \n500 书籍\n请输入数据\n用一个空格隔开\n=='
            mc.set(from_user_name, '2', 180)
        elif content == '3':
            content = '输入月份\n#普通查询#\n直接输入月份\n示例: 1\n#高级查询#\n'
            content += '①指定月份与年份（2014年12月）：\n12 2014\n' \
                       '②当前年1月到2月份：\n1 2\n' \
                       '③2013年2月到2014年5月：\n2 5 2013 2014'
            mc.set(from_user_name, '3', 180)
        elif content == '4':
            content = '为了能正确的下载请用非微信自带浏览器打开\n如果你不幸忘记密码,请在反馈中联系[要记账]\n\n' \
                      '导出账单：<a href=\'http://yaojizhang.sinaapp.com/export-csv/' + from_user_name + '\'>导出</a>'
            # mc.set(from_user_name, '4', 180)
        elif content == '5':
            content = '①首先要创建账本,输入您设置的密码,该密码以后用来提取数据.\n②您可以输入消费信息啦\n'
        elif content == '6':
            content = '回复Y确认'
            mc.set(from_user_name, '6', 180)
        elif content == '7':
            content = '把您的建议和意见以及疑问都写下来吧~'
            mc.set(from_user_name, '7', 180)
        else:
            content = '[要记账]猜你要这个吧\n\n1.创建账本\n2.增加记录\n3.查询\n4.导出账单\n5.帮助\n6.删除账号并清空数据\n7.反馈'

    return get_reply_xml(msg.get('FromUserName'), msg.get('ToUserName'), content)


def is_number(num):
    try:
        float(num)
        return True
    except:
        return False
        #elif msg_type == 'text':


#handle download csv
def export_csv(request, id_user):
    error = False
    pwd_user = ''
    valid = False
    print 'user id : ' + id_user
    if 'pwd_user' in request.GET:
        pwd_user = request.GET['pwd_user']
        if len(pwd_user) == 0:
            error = True
        else:
            print pwd_user
            u1 = User.objects.get(user=id_user)
            if u1.pwd == pwd_user:
                valid = True
            else:
                valid = False
                error = True

    if valid:
        u1 = User.objects.get(user=id_user)
        pb = PayBooks.objects.filter(user=u1)
        current_year = time.strftime('%Y')
        '''从2013年开始遍历,到当前年停止
        1.年份为空直接跳过
        2.如果过滤到该月份条数为零则输出空'''

        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename = bill.csv'
        # 防止瘟到死下乱码
        response.write(codecs.BOM_UTF8)

        # create CSV writer
        writer = csv.writer(response, dialect='excel')
        writer.writerow(['要记账账单导出'])
        for i in range(2013, int(current_year)+1):
            pb_temp = pb.filter(year=i)
            if pb_temp.count() != 0:
                writer.writerow([str(i)+'年'])
                for j in range(1, 13):
                    pb_month = pb_temp.filter(month=j)
                    if pb_month.count() == 0:
                        writer.writerow([str(j)+'月', '空'])
                        continue
                    else:
                        writer.writerow([str(j)+'月'])
                        writer.writerow(['', '日', '金额', '备注'])
                        for pb_each in pb_month:
                            day = pb_each.stamp
                            writer.writerow(['',
                                             "{}".format(day[2]+day[3]),
                                            "{}".format(pb_each.money),
                                            "{}".format(pb_each.remark.encode('utf8'))])
                        writer.writerow(['', "月结", "{}".format(pb_month.aggregate(Sum('money')).values()[0])])
                writer.writerow(["年结", "{}".format(pb_temp.aggregate(Sum('money')).values()[0])])

        #writer.writerow(['2014', '01', '02', '154', '测试'])
        return response
    return render_to_response('export_csv.html', {'error': error})


