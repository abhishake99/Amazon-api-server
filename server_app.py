from flask import Flask, request,jsonify
import json
import requests
from parsel import Selector
import time
from lxml import etree
from dateutil.parser import parse
from datetime import datetime

app = Flask(__name__)



region='IND'

countries_base_urls = {
        "US": "https://www.amazon.com",
        "GB": "https://www.amazon.co.uk",
        "UK": "https://www.amazon.co.uk",
        "DE": "https://www.amazon.de",
        "ES": "https://www.amazon.es",
        "IT": "https://www.amazon.it",
        "IND":"https://www.amazon.in"
    }

AMAZON_US_URL=countries_base_urls[region]

AMAZON_ADDRESS_CHANGE_URL = AMAZON_US_URL+"/portal-migration/hz/glow/address-change"

AMAZON_CSRF_TOKEN_URL = AMAZON_US_URL+"/portal-migration/hz/glow/get-rendered-address-selections?deviceType=desktop&pageType=Search&storeContext=NoStoreName&actionSource=desktop-modal"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

DEFAULT_REQUEST_HEADERS = {"Accept-Language": "en", "User-Agent": DEFAULT_USER_AGENT}




def get_amazon_content(start_url: str, cookies: dict = None) -> tuple:
    response = requests.get(
        url=start_url, headers=DEFAULT_REQUEST_HEADERS, cookies=cookies
    )
    response.raise_for_status()
    return Selector(text=response.text), response.cookies


def get_ajax_token(content: Selector):
    data = content.xpath(
        "//span[@id='nav-global-location-data-modal-action']/@data-a-modal"
    ).get()
    if not data:
        raise ValueError("Invalid page content")
    json_data = json.loads(data)
    return json_data["ajaxHeaders"]["anti-csrftoken-a2z"]


def get_session_id(content: Selector):
    session_id = content.re_first(r'session: \{id: "(.+?)"')
    if not session_id:
        raise ValueError("Session id not found")
    return session_id


def get_token(content: Selector):
    csrf_token = content.re_first(r'CSRF_TOKEN : "(.+?)"')
    if not csrf_token:
        raise ValueError("CSRF token not found")
    return csrf_token


def send_change_location_request(zip_code: str, headers: dict, cookies: dict):
    local_headers = {
    'accept': 'text/html,*/*',
    'accept-language': 'en-US,en;q=0.9',
    'anti-csrftoken-a2z': headers['anti-csrftoken-a2z'],
    'connection': 'keep-alive',
    'content-type': 'application/json',
    'device-memory': '8',
    'downlink': '10',
    'dpr': '1.25',
    'ect': '4g',
    'host': 'www.amazon.in',
    'origin': 'https://www.amazon.in',
    'referer': 'https://www.amazon.in/',
    'rtt': '100',
    'sec-ch-device-memory': '8',
    'sec-ch-dpr': '1.25',
    'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"15.0.0"',
    'sec-ch-viewport-width': '767',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'viewport-width': '767',
    'x-requested-with': 'XMLHttpRequest',
    }
    json_data={
            "locationType": "LOCATION_INPUT",
            "zipCode": zip_code,
            "storeContext": "generic",
            "deviceType": "web",
            "pageType": "Gateway",
            "actionSource": "glow",
        }
    params={
                'actionSource': 'glow'
            }
    response = requests.post(
        AMAZON_ADDRESS_CHANGE_URL,
        json=json_data,
        params=params,
        headers=local_headers,
        cookies=cookies
    )
    return response.cookies


def get_session_cookies(zip_code: str):
    response = requests.get(url=AMAZON_US_URL, headers=DEFAULT_REQUEST_HEADERS)
    content = Selector(text=response.text)


    headers = {
        "anti-csrftoken-a2z": get_ajax_token(content=content),
        "user-agent": DEFAULT_USER_AGENT,
    }

    store_cookie_1={}
    for cook in  response.cookies:
        store_cookie_1[cook.name]=cook.value
    params = {
    'deviceType': 'desktop',
    'pageType': 'Gateway',
    'storeContext': 'NoStoreName',
    'actionSource': 'desktop-modal',
    }

    response = requests.get(
        url=AMAZON_CSRF_TOKEN_URL, headers=headers, cookies=response.cookies,params=params
    )
    content = Selector(text=response.text)
    headers = {
        "anti-csrftoken-a2z": get_token(content=content),
        "user-agent": DEFAULT_USER_AGENT,
    }
    changed_cookie=dict(response.cookies)
    changed_cookie['session-id']=store_cookie_1['session-id']
    final_cookies=send_change_location_request(
        zip_code=zip_code, headers=headers, cookies=changed_cookie
    )
    response = requests.get(
        url=AMAZON_US_URL, headers=DEFAULT_REQUEST_HEADERS, cookies=final_cookies
    )
    content = Selector(text=response.text)
    location_label = content.css("span#glow-ingress-line2::text").get().strip()
    if zip_code not in location_label:
        return False
    return final_cookies


def get_data(codes, locations):
    headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'device-memory': '8',
            'downlink': '1.45',
            'dpr': '1.25',
            'ect': '3g',
            'host': 'www.amazon.in',
            'rtt': '300',
            'sec-ch-device-memory': '8',
            'sec-ch-dpr': '1.25',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"15.0.0"',
            'sec-ch-viewport-width': '1536',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'viewport-width': '1536',
        }
    params = {
                'th': '1',
            }

    result=[]

    t=datetime.now()
    time.sleep(5)
    for loc in locations:
        loc=str(loc)
        check=True
        #print(loc)
        time.sleep(5)
        try:
            cookies2=get_session_cookies(zip_code=loc)
        except:
            print(f"Did not get valid response for {loc} trying one more time in 10 sec")
            time.sleep(10)
            try:
                cookies2=get_session_cookies(zip_code=loc)
            except:
                print(f"The pin code {loc} is not valid")
        if cookies2!=False:
            print(f"Started Getting data for {loc} pin")
            for code in codes:
                curr_code=code
                prod_url='https://www.amazon.in/dp/{0}'.format(curr_code)
                #print(cookies2)
                time.sleep(2)
                response = requests.get(prod_url, params=params, cookies=cookies2, headers=headers)
                if response.status_code!=200:
                    time.sleep(3)
                    response = requests.get(prod_url, params=params, cookies=cookies2, headers=headers)       
                html=response.text
                dom=etree.HTML(html)

                del_info=dom.xpath('//div[@id="contextualIngressPtLabel_deliveryShortLine"]/span/text()')
                del_info=''.join(del_info)

                status = dom.xpath('.//div[@id="unqualifiedBuyBox"]//span[@id="buybox-see-all-buying-choices"]/span/a/text()') \
                        or dom.xpath('//span[@id="submit.add-to-cart-announce"]/text()')\
                        or dom.xpath('.//div[@id="outOfStock"]//span[@class="a-color-price a-text-bold"]/text()')\
                        or dom.xpath('.//div[@id="availability"]/span//text()')\
                        or dom.xpath("//span[@class='a-button a-spacing-small a-button-primary a-button-icon']/span/span/text()")\
                        or dom.xpath("//span[@class='a-button a-spacing-base a-button-base']/span/a/text()")\
                        or dom.xpath("//div[@id='outOfStock']/div/div/span/text()")\
                        or dom.xpath("//div[@id='ddmDeliveryMessage']/span/text()")\
                        or dom.xpath("//div[@id='availability-string']//text()")\
                        or dom.xpath("//div[@id='availability-string']//span/text()")\
                        or dom.xpath('.//b[contains(text(),"Looking for something?")]//text()')
                status = ''.join(status).strip()

                if loc not in del_info and 'Looking for something' not in status:
                    print("Refreshing Cookies")
                    time.sleep(2)
                    cookies2=get_session_cookies(zip_code=loc)
                    response = requests.get(prod_url, params=params, cookies=cookies2, headers=headers)
                    html=response.text
                    dom=etree.HTML(html)
                    del_info=dom.xpath('//div[@id="contextualIngressPtLabel_deliveryShortLine"]/span/text()')
                    del_info=''.join(del_info)

                print("Delivery info : ",del_info)
                
                name=dom.xpath('//span[@id="productTitle"]/text()')
                name=''.join(name)             

                sellers = dom.xpath("(//div[@id='merchant-info']/a)[1]/text()")\
                        or dom.xpath("(//div[@id='merchant-info']/a)[1]/span/text()")\
                        or dom.xpath("(//a[@id='sellerProfileTriggerId'])[1]//text()")\
                        or dom.xpath("//div[@id='freshShipsFromSoldBy_feature_div']//a/text()")
                sellers = ''.join(sellers).strip()

                review = dom.xpath("(//span[@id='acrCustomerReviewText'])[1]/text()")
                review = ''.join(review).strip()

                rating = dom.xpath("(//span[@class='a-size-medium a-color-base'])[contains(text(),'out of 5')]/text()")
                rating = ''.join(rating).strip()

                status = dom.xpath('.//div[@id="unqualifiedBuyBox"]//span[@id="buybox-see-all-buying-choices"]/span/a/text()') \
                        or dom.xpath('//span[@id="submit.add-to-cart-announce"]/text()')\
                        or dom.xpath('.//div[@id="outOfStock"]//span[@class="a-color-price a-text-bold"]/text()')\
                        or dom.xpath('.//div[@id="availability"]/span//text()')\
                        or dom.xpath("//span[@class='a-button a-spacing-small a-button-primary a-button-icon']/span/span/text()")\
                        or dom.xpath("//span[@class='a-button a-spacing-base a-button-base']/span/a/text()")\
                        or dom.xpath("//div[@id='outOfStock']/div/div/span/text()")\
                        or dom.xpath("//div[@id='ddmDeliveryMessage']/span/text()")\
                        or dom.xpath("//div[@id='availability-string']//text()")\
                        or dom.xpath("//div[@id='availability-string']//span/text()")\
                        or dom.xpath('.//b[contains(text(),"Looking for something?")]//text()')
                status = ''.join(status).strip()

                check_fresh=dom.xpath('//img[contains(@class,"alm-mod-logo")]//@src')\
                            or dom.xpath('//div[contains(@id,"almLogoAndDeliveryMessage_feature_div")]//span[@class="a-size-base a-color-secondary a-text-normal"]/text()')\
                            
                check_fresh=''.join(check_fresh)
                if 'Fresh items' in check_fresh or 'http' in check_fresh :
                    status='Currently Unavailable'


                sp =  dom.xpath('//td[contains(text(),"Deal Price:")]/parent::tr//span[contains(@class,"PriceToPay")]/span[contains(@class,"offscreen")]//text()')\
                    or dom.xpath('(//span[contains(@class,"priceToPay")])[1]/span//span[contains(@class,"price")]/text()')\
                    or dom.xpath('//div[contains(@id,"a_desktop")]//span[contains(@class,"priceToPay")]//span[contains(@class,"a-price")]//text()')\
                    or dom.xpath('//span[contains(@class,"priceToPay")]//span[contains(@class,"a-price")]//text()')\
                    or dom.xpath('(//span[contains(@class, "priceToPay")]//span[@class="a-offscreen"])[1]/text()')\
                    or dom.xpath('(.//td[contains(text(),"Deal of the Day:")]/following::span[1]/span[1])[1]/text()')\
                    or dom.xpath('(//td[contains(text(),"Deal of the Day:")]/following::span[1])[1]/text()')\
                    or dom.xpath('.//div[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[1]/span/text()')\
                    or dom.xpath('.//div[@class="a-section a-spacing-none aok-align-center"]//span[@class="a-price aok-align-center priceToPay"]/span[1]/text()')\
                    or dom.xpath("//span[@id='priceblock_ourprice']/span/text()")\
                    or dom.xpath("//div[contains(@id,'core')][contains(@id,'Price')]//span[contains(@class,'price')][contains(@class,'Pay')]/span[contains(@class,'offscreen')]/text()")\
                    or dom.xpath("//div[@id='booksHeaderInfoContainer']//span[@id='price']/text()")
                price = ''.join(sp).strip()

                try:
                    if str(price).count('₹')>1:
                        price='₹ '+str(price.split('₹')[1])
                except:
                    pass                  
                
                dod1 = dom.xpath('//span[@class="dealBadge"]//span[contains(text(),"Deal")]//text()')\
                    or dom.xpath("//td[contains(text(),'Deal of the Day:')]/ancestor::tr//text()")\
                    or dom.xpath('//span[@class="a-size-base dealBadgeSupportingText a-text-bold"]//span//text()')\
                    or dom.xpath('//div/div[contains(@id,"deal")][contains(@id,"adge")]/span[contains(@class,"deal")][contains(@class,"adge")]//text()')
                dod = ''.join(dod1).strip()

                light1 = dom.xpath('//div[@class="a-section a-spacing-none a-padding-none a-size-small"]/span/text()')
                light = ''.join(light1).strip()

                dealprice1 = dom.xpath("//td[contains(text(),'Deal Price:')]/ancestor::tr//text()")
                dealprice = ''.join(dealprice1).strip()

                if len(dealprice) !=0 and len(light) !=0:
                    lightning=light
                elif len(dod) !=0:
                    lightning='Deal of the day '
                elif len(dealprice)!=0:
                    lightning='Limited time deal ' 
                else:
                    lightning=''

                coupons = dom.xpath('(//label[contains(@id,"couponText")])[1]/text()')\
                or dom.xpath('(//div[@id="vpcButton"])[1]//span[@class="a-color-base a-text-bold"]/text()')\
                or dom.xpath('//div[@id="promoPriceBlockMessage_feature_div"]//label[contains(@id, "couponText")]//text()')\
                or dom.xpath('.//i[contains(text(),"Coupon")]/following::td[1]/div[1]/div/div//text()')
                coupon=''.join(coupons).strip()

                subscribes= dom.xpath('.//span[contains(text()," Subscribe & Save: ")]/parent::div/span//text()') 
                subscribe=''.join(subscribes)
                import re
                subscribe = re.sub(r'\s+', ' ', subscribe)

                asin2 = dom.xpath('.//div[@id="page-refresh-js-initializer_feature_div"]/script[3]/text()')    
                asin_web = ''.join(asin2).strip()
                try:
                    asin_web = json.loads(asin_web)
                    asin_web = asin_web['pageRefreshUrlParams']['asinList']
                except:
                    asin2 =   dom.xpath('(//input[@id="ASIN"])[1]/@value')\
                    or dom.xpath('(//input[@id="ddmSelectAsin"])[1]/@value')\
                    or dom.xpath('//tr/*[contains(text(),"ASIN")]/following::td[1]/text()')\
                    or dom.xpath('//span[@class="a-list-item"]/span[contains(text(),"ASIN")]/following::span[1]/text()')\
                    or dom.xpath("//*[contains(text(),'ASIN')]/following::*[starts-with(text(),'B0')]/text()")\
                    or dom.xpath("//*[contains(text(),'ASIN')]/following::*[starts-with(text(),' B0')]/text()")
                    asin_web = ''.join(asin2).strip()

                delivery_date1 =  dom.xpath("//span[@id='upsell-message']/b/text()")\
                            or dom.xpath("(//span[(contains(@data-csa-c-delivery-price, 'FREE'))])[1]/@data-csa-c-delivery-time")\
                            or dom.xpath("(//div[(contains(@id, 'DELIVERY_MESSAGE'))])[1]//b/text()")\
                            or dom.xpath("(//span[(contains(@data-csa-c-mir-type, 'DELIVERY'))])[1]/@data-csa-c-delivery-time")
                
                fastest_del=dom.xpath("(//span[(contains(@data-csa-c-delivery-price, 'fastest'))])[1]/@data-csa-c-delivery-time")
                fastest_del=''.join(fastest_del)

                delivery_date = ''.join(delivery_date1).strip()
                delivery_date = delivery_date.strip()

                if delivery_date=='':
                    delivery_date=fastest_del
                #delivery_date = delivery_date.split('-')[0]
                try:
                    delivery_date=delivery_date.split('-')[1]
                except:
                    pass            
                times=t.strftime("%d-%m-%y")
                if delivery_date1:
                    try:
                        dt1 = parse(delivery_date)
                        dt1 = dt1.strftime('%d-%m-%y')
                        mdate1 = datetime.strptime(dt1, "%d-%m-%y").date()
                        rdate1 = datetime.strptime(times, "%d-%m-%y").date()
                        delta = (mdate1 - rdate1).days
                        if '-' in str(delta):
                            delta=365+delta
                        #print(delta)
                        delta=str(round(delta,0))
                    except:

                        delta = ''
                else:
                        delta = ''
                        #print(delta)

                fastest = ''.join(delivery_date1).strip()
                if 'Tomorrow' in fastest or 'Today' in fastest:
                    delta='1'

                delivery_fee= dom.xpath("(//div[contains(@id,'DELIVERY_MESSAGE_LARGE')]/span[@data-csa-c-delivery-type='delivery'])[1]/@data-csa-c-delivery-price")
                delivery_fee= ''.join(delivery_fee).strip()

            
                parent_asin= dom.xpath("//script[@type='text/javascript'][contains(text(),'parentAsin')][not(contains(text(),'&parentAsin'))]/text()") 
                parent_asin=''.join(parent_asin) 
                try: 
                    parent_asin=parent_asin.split(',"parentAsin":"')[-1].split('",')[0].strip()
                except: 
                    parent_asin='' 

                #if 'no_of_ratings' in extras:
                no_of_ratings=dom.xpath('(//span[@id="acrCustomerReviewText"])[1]//text()')
                no_of_ratings=''.join(no_of_ratings)
                no_of_ratings=no_of_ratings.replace('ratings','').strip()  
                
                    
                unit_sold=dom.xpath('//span[contains(@class,"social-proofing")]//span//text()')
                unit_sold=''.join(unit_sold)
                unit_sold=unit_sold.replace('K+','000+')
                
                platform='Amazon'

                dict1={}
                dict1["time_stamp"]=times
                dict1["platform"]=platform
                dict1["platform_code"]=code
                dict1["location"]=loc
                dict1["pname"]=name
                dict1["sp"]=price
                dict1["rating"]=rating
                dict1["seller"]=sellers
                dict1["prod_url"]=prod_url
                dict1["status_text"]=status
                dict1["deal"]=lightning
                dict1["coupon"]=coupon
                dict1["sns"]=subscribe
                dict1["delivery_days"]=delta
                dict1["delivery_fee"]=delivery_fee
                dict1["defaultasin"]=asin_web
                dict1["parent_asin"]=parent_asin
                dict1["no_of_ratings"]=no_of_ratings
                dict1["unit_sold"]=unit_sold
                print(dict1)
                result.append(dict1)
        else:
            print(f"The pin code {loc} is not valid")
    return result

@app.route('/getdata', methods=['GET'])
def get_request():

    data=request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Extract fields from JSON
    asins = data.get('asin')
    locations = data.get('location')
    print(asins,locations)

    if len(asins)==0 or len(locations)==0:
        return jsonify({"error": "List cannot be empty"}), 400
    final_results=get_data(
        asins,
        locations
    )
    return final_results

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0",port=5000)