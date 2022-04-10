import json
import time
import requests
import argparse
import datetime


parser = argparse.ArgumentParser()

parser.add_argument('-u', '--user', default='default', help='load user config')
parser.add_argument('-d', '--device', default='default', help='load device config')
parser.add_argument('-b', '--bark', default='default', help='load bark config')

args = parser.parse_args()

with open(f'config/user.{args.user}.json', 'r') as f:
    user_config = json.load(f)

with open(f'config/device.{args.device}.json', 'r') as f:
    device_config = json.load(f)

with open(f'config/bark.{args.bark}.json', 'r') as f:
    bark_config = json.load(f)


BARK_ID = bark_config['BARK_ID']

COOKIE = user_config['COOKIE']
DDMC_UID = user_config['DDMC_UID']
DEFAULT_ADDR_NO = user_config['DEFAULT_ADDR_NO']

DEVICE_ID = device_config['DEVICE_ID']
DEVICE_TOKEN = device_config['DEVICE_TOKEN']


def init():
    headers = {
        'Host': 'sunquan.api.ddxq.mobi',
        'Accept': '*/*',
        'User-Agent': 'neighborhood/9.49.1 (iPhone; iOS 15.4.1; Scale/3.00)',
        'Content-Type': 'application/x-www-form-urlencoded',
        'ddmc-uid': DDMC_UID,
        'ddmc-city-number': '0101',
        'ddmc-locale-identifier': 'zh_CN',
        'ddmc-device-id': DEVICE_ID,
        'ddmc-device-token': DEVICE_TOKEN,
        'ddmc-device-name': 'iPhone 12 Pro',
        'ddmc-device-model': 'iPhone13,3',
        'ddmc-channel': 'App Store',
        'ddmc-os-version': '15.4.1',
        'ddmc-api-version': '9.49.2',
        'ddmc-build-version': '1221',
        'ddmc-app-client-id': '1',
        'ddmc-country-code': 'CN',
        'ddmc-language-code': 'zh',
        'Accept-Language': 'zh-Hans-CN;q=1',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cookie': COOKIE
    }

    params = {
        "api_version": "9.49.2",
        "app_version": "1221",
        'buildVersion': "1221",
        "app_client_id": "1",
        'channel': 'App Store',
        'city_number': '0101',
        'device_id': DEVICE_ID,
        'device_model': 'iPhone13,3',
        'device_name': 'iPhone 12 Pro',
        'device_token': DEVICE_TOKEN,
        'os_version': '15.4.1',
        'uid': DDMC_UID
    }
    return headers, params


def post_request(url, method, headers, params):
    for _ in range(20):
        time.sleep(0.1)
        if method == 'POST':
            r = requests.post(url, headers=headers, params=params)
        else:
            r = requests.get(url, headers=headers, params=params)

        if r.status_code != 200:
            print(url, r.status_code, 'ResStatusError!')
            continue

        try:
            response = r.json()
        except json.JSONDecodeError:
            print(url, 'JSONDecodeError!')
            continue

        if response['code'] == 0 or response['code'] == 5001: # 5001 预订单
            return response['data']
        elif response['code'] == -3000:
            print(url, 'Busy!')
            continue
        elif response['code'] == -3100:
            print(url, 'DataLoadError')
            continue
        elif response['code'] == 5003:
            print('送达时间已抢光')
            break
        elif response['code'] == 5014:
            print('暂未营业，等待开放')
            while datetime.datetime.now() < datetime.datetime.now().replace(hour=5, minute=57, second=0, microsecond=0):
                time.sleep(1)
            continue
        else:
            print(r.json())
            print(url, response['code'], 'OtherDataError!')
            continue
    else:
        return {}


def get_addresses(headers, params):
    ret = post_request(url='https://sunquan.api.ddxq.mobi/api/v1/user/address/', method='GET', headers=headers, params=params)
    if 'valid_address' in ret:
        return ret['valid_address']
    else:
        return []


def get_cart_products(headers, params):
    ret = post_request(url='https://maicai.api.ddxq.mobi/cart/index', method='POST', headers=headers, params={**params, **{
        'is_load': 1,
        'ab_config': '{"key_no_condition_barter":false,"key_show_cart_barter":"0","key_cart_discount_price":"C"}'
    }})
    return ret


def check_order(headers, params, products):
    packages = {
        'package_type': 1,
        'package_id': 1,
        'products': products,
    },

    ret = post_request(url='https://maicai.api.ddxq.mobi/order/checkOrder', method='POST', headers=headers, params={**params, **{
        'check_order_type': '0',
        'user_ticket_id': 'default',
        'freight_ticket_id': 'default',
        'is_use_point': '0',
        'is_use_balance': '0',
        'is_buy_vip': '0',
        'is_buy_coupons': '0',
        'coupons_id': '',
        'packages': json.dumps(packages),
    }})

    if 'order' in ret:
        return ret['order']
    else:
        return {}


def get_multi_reserve_time(headers, params, products):
    ret = post_request(url='https://maicai.api.ddxq.mobi/order/getMultiReserveTime', method='POST', headers=headers, params={**params, **{
        'products': json.dumps([products])
    }})
    return ret


def add_new_order(headers, params, order, address, cart_info, order_products, reserve_time):
    package_order = {
        'packages': [{
            'first_selected_big_time': '1',
            'products': order_products,
            'eta_trace_id': '',
            'package_id': 1,
            'package_type': '1',
            'reserved_time_start': reserve_time['start_timestamp'],
            'reserved_time_end': reserve_time['end_timestamp'],
            'soon_arrival': 0,
        }],
        'payment_order': {
            'reserved_time_start': reserve_time['start_timestamp'],
            'reserved_time_end': reserve_time['end_timestamp'],
            'freight_discount_money': order['freight_discount_money'],
            'freight_money': order['freight_money'],
            'order_freight': '0.00', # 运费
            'address_id': address['id'],
            'used_point_num': 0,
            'is_use_balance': 0, # 余额
            'order_type': 1,
            'pay_type': 2, # 支付宝
            'parent_order_sign': cart_info['parent_order_info']['parent_order_sign'],
            'receipt_without_sku': '0',
            'price': order['total_money'],
            # 'current_position', '',
        }
    }

    ret = post_request(url='https://maicai.api.ddxq.mobi/order/addNewOrder', method='POST', headers=headers, params={**params, **{
        'ab_config': '{"key_no_condition_barter":false}',
        'package_order': json.dumps(package_order),
        'clientDetail': {},
    }})
    return ret


def job():

    headers, params = init()

    addresses = get_addresses(headers, params)

    if len(addresses) == 0:
        print('未查询到有效收货地址，请前往 App 添加或检查 cookie 是否正确！')
        exit()

    print('########## 选择收货地址 ##########')

    for idx, address in enumerate(addresses):
        if idx == DEFAULT_ADDR_NO:
            print('*', idx, address['location']['name'])
        else:
            print(idx, address['location']['name'])

    if len(addresses) == 1:
        address_no = 0
    elif 0 <= DEFAULT_ADDR_NO < len(addresses):
        address_no = DEFAULT_ADDR_NO
    else:
        address_no = input('请输入地址序号（0, 1, 2...): ')

        if address_no.isdigit and 0 <= int(address_no) < len(addresses):
            address_no = int(address_no)
        else:
            print('输入范围不正确')
            exit(0)

    address = addresses[address_no]

    params = {**params, **{
        'ab_config': '{"ETA_time_default_selection":"B1.2"}',
        'city_number': address['city_number'],
        'station_id': address['station_id'],
        'address_id': address['id'],
    }}

    headers = {**headers, **{
        'Host': 'maicai.api.ddxq.mobi',
        'ddmc-city-number': address['city_number'],
        'ddmc-station-id': address['station_id'],
    }}

    while True:

        time.sleep(0.8)

        print('########## 有效商品列表 ###########')
        cart_info = get_cart_products(headers=headers, params=params)
        if not cart_info:
            continue
        
        if len(cart_info['product']['effective']) > 0:
            products =  cart_info['product']['effective'][0]['products'] # 所有有效商品（不包括换购）
        elif 'new_order_product_list' in cart_info and len(cart_info['new_order_product_list']) > 0:
            products = cart_info['new_order_product_list'][0]['products'] # 所有勾选商品（包括换购)
        else:
            products = []

        if len(products) == 0:
            print('购物车中无有效商品，请先前往 App 添加并勾选！')
            time.sleep(30)
            continue
        else:
            for product in products:
                print(product['product_name'])

        order_products = []
        for product in products:
            # order_sort sale_batches type 'category_path', 'price_type' 'activity_id', 'conditions_num'
            order_product = {k: product[k] for k in ['id', 'count', 'price', 'origin_price', 'sizes']}
            order_product['total_money'] = product['total_price']
            # order_product['is_coupon_gift'] = 0
            # order_product['batch_type'] = -1

            if 'total_origin_price' in product:
                order_product['total_origin_money'] = product['total_origin_price']
            else:
                order_product['total_origin_money'] = product['origin_price']
                
            if 'instant_rebate_money' in product:
                order_product['instant_rebate_money'] = product['instant_rebate_money']
            else:
                order_product['instant_rebate_money'] = '0.00'

            # if 'product_type' in product:
            #     order_product['product_type'] = product['product_type']
            # # else:
            # #     order_product['product_type'] = 0
            
            # if 'order_sort' in product:
            #     order_product['order_sort'] = product['order_sort']
            # else:
            #     order_product['order_sort'] = 0
            
            # if 'sale_batches' in product:
            #     order_product['sale_batches'] = product['sale_batches']
            # else:
            #     order_product['sale_batches'] = 0

            order_products.append(order_product)

        time.sleep(0.8)

        print('########## 生成订单信息 ###########')
        order = check_order(headers=headers, params=params, products=order_products)
        if not order:
            continue
        print('订单总金额：', order['total_money'])

        time.sleep(0.8)
        print('########## 获取预约时间 ###########')
        reserve_times = get_multi_reserve_time(headers, params, order_products)
        if not reserve_times:
            continue
        reserve_times = reserve_times[0]['time'][0]['times']
        reserve_times = [t for t in reserve_times if t['disableType'] == 0]

        if len(reserve_times) == 0:
            print('暂无可预约时间')
            continue
        else:
            for t in reserve_times:
                print(t['arrival_time_msg'])
            reserve_time = reserve_times[0]

        time.sleep(1)
        print('########## 立即支付购买 ###########')

        new_order = add_new_order(headers=headers, params=params, order=order, address=address, cart_info=cart_info, order_products=order_products, reserve_time=reserve_time)
        if not new_order:
            continue
        print(new_order)

        if BARK_ID:
            requests.get(url = f'https://api.day.app/{BARK_ID}/叮咚买菜/{args.user} 买到了！' + '?sound=minuet&level=timeSensitive')

        exit()


if __name__ == "__main__":
    while True:
        job()
