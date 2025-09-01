import time

dick1 ={
  "NEXT_LOCALE": "uk",
  "arkham_session": "771e04a6-3694-4aa1-b36f-5a952bd8190f",
  "arkham_is_authed": "true",
  "arkham_captcha_token": "7b2a3596-8024-468c-a385-9f5231068894"
}

dick2 ={'time': 'asdad'}
dick3 = dict(dick1, **dick2)
dict_no_time = dick3.copy()
dict_no_time.pop('time', None)

print(int(time.time()))