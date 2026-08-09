from collections import Counter
from PIL import Image
im=Image.open('/tmp/qss-partition-fixed.png').convert('RGB')
w,h=im.size
print('SIZE',im.size)
for name,box in {
 'full':(0,0,w,h),
 'sidebar':(0,0,w//4,h),
 'content':(w//4,0,w,h),
 'content_top':(w//4,0,w,h//2),
 'content_bottom':(w//4,h//2,w,h),
}.items():
 c=im.crop(box).resize((200,120))
 vals=[(r+g+b)/3 for r,g,b in c.getdata()]
 print(name,'mean',round(sum(vals)/len(vals),1),'bright%',round(sum(v>220 for v in vals)/len(vals)*100,1),'dark%',round(sum(v<45 for v in vals)/len(vals)*100,1))
print('COMMON')
for col,n in Counter(im.resize((160,100)).getdata()).most_common(12): print(col,n)
