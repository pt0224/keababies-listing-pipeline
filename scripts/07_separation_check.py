# -*- coding: utf-8 -*-
"""deltaE2000 separation matrix for the 5 Atlas variants -- catches any pair that
will read as 'the same colour' in a thumbnail."""
import json, math, itertools

V = json.load(open(r"F:\_KEA WORLD\KEA BABIES\FEED\Assets\variants.json", encoding="utf-8"))["variants"]

def de2000(l1, l2):
    L1,a1,b1 = l1; L2,a2,b2 = l2
    dLp=L2-L1; Lb=(L1+L2)/2
    C1=math.hypot(a1,b1); C2=math.hypot(a2,b2); Cb=(C1+C2)/2
    G=0.5*(1-math.sqrt(Cb**7/(Cb**7+25**7))) if Cb>0 else 0
    a1p=a1*(1+G); a2p=a2*(1+G)
    C1p=math.hypot(a1p,b1); C2p=math.hypot(a2p,b2); dCp=C2p-C1p; Cbp=(C1p+C2p)/2
    h1=math.degrees(math.atan2(b1,a1p))%360; h2=math.degrees(math.atan2(b2,a2p))%360
    dh=h2-h1
    if abs(dh)>180: dh-=360*(1 if dh>0 else -1)
    dHp=2*math.sqrt(C1p*C2p)*math.sin(math.radians(dh/2))
    Hbp=(h1+h2)/2
    if abs(h1-h2)>180: Hbp+=180
    T=1-0.17*math.cos(math.radians(Hbp-30))+0.24*math.cos(math.radians(2*Hbp))+0.32*math.cos(math.radians(3*Hbp+6))-0.20*math.cos(math.radians(4*Hbp-63))
    Sl=1+(0.015*(Lb-50)**2)/math.sqrt(20+(Lb-50)**2); Sc=1+0.045*Cbp; Sh=1+0.015*Cbp*T
    Rt=-2*math.sqrt(Cbp**7/(Cbp**7+25**7))*math.sin(math.radians(60*math.exp(-(((Hbp-275)/25)**2)))) if Cbp>0 else 0
    return math.sqrt((dLp/Sl)**2+(dCp/Sc)**2+(dHp/Sh)**2+Rt*(dCp/Sc)*(dHp/Sh))

names=[v["name"] for v in V]
print(f"{'':18s}" + "".join(f"{n[:11]:>13s}" for n in names))
worst=(999,None)
for i,a in enumerate(V):
    row=f"{a['name'][:18]:18s}"
    for j,b in enumerate(V):
        d=de2000(a["lab"],b["lab"])
        row+=f"{('-' if i==j else f'{d:.1f}'):>13s}"
        if i<j and d<worst[0]: worst=(d,(a['name'],b['name']))
    print(row)
print(f"\nCLOSEST PAIR: {worst[1][0]} <-> {worst[1][1]}  dE2000 = {worst[0]:.2f}")
print("guide: <1 invisible | 1-2 expert-only | 2-5 noticeable | >5 clearly distinct")
