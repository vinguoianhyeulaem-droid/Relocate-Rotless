#!/usr/bin/env python3
"""Relocate rootless FINAL 0.1.23 - single standalone reproducible patch.

Preserves the exact tested 0.1.23 Tweak.xm produced by the 0.1.22 merged
patch followed by patch_relocate_023.py. No diagnostic logging added.

Run once on the same CLEAN Tweak/Tweak.xm used for the prior builds:
    python3 patch_relocate_final_023.py Tweak/Tweak.xm

It also updates Tweak/Relocate.plist (or root Relocate.plist).
This patch intentionally refuses unknown/customized source rather than
silently overwriting user changes. Run on a clean Git checkout.
"""
from pathlib import Path
import base64
import hashlib
import re
import sys
import zlib

CLEAN_SHA256 = "56b6aad7a222eb382fbb2b74b509b0c10ba671c2ebedc1f7e9cb7781c0c40883"
FINAL_SHA256 = "bf57b70dd6e0649ed559071df9a64d2ffb166ef86335b8e6cd1736d73da51164"
FINAL_TWEAK_COMPRESSED_B85 = (
    'c-q}OYjYbnlHd6&V5RIOWtpU$^=^)eV#$)7=pxHLQ%<tQa9yJrkVG_`nVp9u+VTImZ&&vZ_a|&OUISoeNJ?V7SLdok96TD0Mx$Q<`YSe1'
    ';xs4U&b@rroqgB(N)=4P*vqYw_a{HHyvP4<mH$`arTNFBIHkSvr`6(!CNs)<KfHLG(g{sz<kQS-uyuY-z02-wt1NkUdUP85Ue4m^wHJ9)'
    'njX`TPQ9GE%?=|kjHkn#`IkSlD2T7ILF=o4PFO_A+tZWb`G>cM=Rc5xt=^TF_I|tIe?oTA3zExek42NXH>cf*CN%fDDGhO4+6`Hj10V}&'
    'vYnJ4d#%<*9ET(g{g;t<5z=5!6imbT!VBxl&f@Ri4rPg#B)SQUa^e>$z|9YhV%`psJc+Knkg1Xgp}dX*D!=D~KqnE)88rKdT}2JGApI6E'
    'G9=Sp>*!Pw_b86jfJHFjr^m$CAA7B{;W6{Eg_kbKb|{-;*<P!T>SWt<ivWuQm>Eqco=?fy@T>?!(tali+-W^&Lv08C`^gIn81hN`#hW*$'
    '9mG|Z9MC90AoC=ob07}Kp$3uzihODj_?ObWNF&nUYkh82fZJ^*UYJqdP7K-W5twBE>DMIp(kab*V*PN@ND_z4U#KR#e;tr_bdu6+M(AWh'
    'fo4~fAe&^w%Zcab1@yx$p-2v^k^@bX7|_kS2<Lpppm7iYkPMj2_xu?Rh|PIdh;&A-XEY*1n&&K<W+acN(~y_4kRoy!$#QQ&fD5iD2YnWk'
    '3D#YwEC-e)Y(fH-T@r(jiI-9WtM0?^i~+ywU~NWIm`6V2bGc%1!9l~mXyG5`ldG5ok^*x6h;G)#@{XjgY<f04XLEXjtN_y>p_k=HGwNTG'
    'eOw%Dc#th3f0o7(axZC*0IuBj#E0hDSV6>p4!8)IZ=a0LhHujtr*Hxr8j#k%$K4G0p3dJVIdt38V1N{D?EAz(=v&h7e*LT?*`jP~q8xF~'
    'E|D?!3DTC60o$>#1TcwH(mopw^Ar{i#0ZF6pgB1h=@y&}LPX8u3s|$>DZ5AkYR_PUIzg3iNwrf4NXojqz|-I?(pP8fdr`mw=qJ{|s0#GY'
    'pIJUTiebHg;onSN0WJe1z<AGsi|a8e!LjT|kRop;N4Wk28?@kwF?sZe=nh>!E<lWaNBS<p_|IGz-DR)R>>>q4WEX#KRevF>4>ZUsyP&86'
    'u?$?7B3X3H(ZQA!?ptH%lqGQ#Wase^RGXj2>EIxfzuH<(b;cGp&zqp>4r4N~RFZ|06k`rf-<t|+LzuZRE&Ln}X`z_V6m+1AVyPB4gr5b_'
    'Le5mo7G_-U*3*tF_Ki|bL9C&hv?9v=sHDn85d|SVITl;-1^)szWRdte?#c!MY(zF;z?{zqAS$*@SZBrj0xGtF3TR>gs1mo49xCI1a9_WQ'
    'Q?MNeoS+{b9(+(l-60B_@z{iqVjIQ!TmT=bah6h!iB6JuKrq>>YgPb#`i5X$t-=QaiT*x|W)$?JB<~K{-4|VGuw#OIx=(LFIQlFP7lhvU'
    'VG+=vOU`-QCvgO&5xs)Bg&;&wIg=t1QvjWY%DHRvldjuWOb_x*&}E<OI?SiWt8M($X<TIV4Iq*-PGc#Ep#1|41wPu6Aiw{vG3o3z=(UL6'
    '<l265R2vFI4Zsn-PQTl+lIqyNOLA2XBfg}Xn5b!EHF*&AB%7gugO-e(Z~}@K?I;&g6eFZ3Swel-9X@Y2^D=Tl!RE@mD*(Qrd3T92gzns+'
    'M#i?LzK$|`Zcz&aL1~+B;pVr9uC>rekGakmzyDrQc_joG@)X9-fk9S@vLG&Cm#h7_5^5YxZx6OkjW_a>5}TT5#*JE>P_Xqm@dQ7t&9lqK'
    '_}pX>`d@}0O2Hk1*8#)%YxBf&;rH3A-wd7;<!;~&HgMo`sl|O<1dda<1^YdERN)i;Z-lsR01nG0418<a2E4jv7nGu9WgNMc_23*R<hy<H'
    '<Ujh|K0<TrzTGFXssWZgD2KKCjRNLW0x(`zl3m6Jfaa#gfUYv!ptppII6zC)2U<n8A%a^<tRd9NX71)P0|}@|3=X$9Y#EDyX7%xk*WP7i'
    'O?KQ_clI3n{WJISosdH5Z?;;G!Q24H72KnIk<boTAHj(%vK?E)P2G0d8A?(%20;Q|k3ahmL;Z)G;GgsOlFEr&)$K>Rc8C1EBw=L`(^K|B'
    'pspd4s&OIc@VA$8#Xd{Q$OwoHnTJ9iw@bQ{?G6|@ibWz-Jg}Rn)s<8d%K&%@u>zy323=Jqa6ry6IRou;*+31s#l5}J>Q;uq%=bWT`z=em'
    '7zmCUI}n4ZB$1`imlPb03|fe_ASfDy_p8`;P%?I9{DJzRYi4oEK7!}$g@?Xhq#hWpnuOIl-3_P#99P%Lt!b6}tw=LkHWc3_<0X^^gTDU8'
    'PztchJSltVBHn1+z(TLQi<DuUAvj&dEPsC5|NqS%rR3Z^o9y<RxxuKD%f7qDLZf;|ag33Zv9rcMP%q#vsJ+ChSkO{8<Dt9A3&8^@Kn*bY'
    'DHmIQb#I9Ff^^xUrtD))+1#5(6eg_@sJ4KiX>+Y7Nd;A!33X3J5#$GpD4bX-E;(c%N8hPP8#Wrdfan}tIS;slmXT0v3X1LAIshFaZwL$3'
    't%aq=NS~~Iw&!x8nzk#WLI(O!Rt^-jv5cOxpo0zVu(_#yYz3ma@n~?7@Q9x1S`#wvl-vA)GB3a@eW1+_JHp1>eUREM!<M7+i$?*+=oI(M'
    'UM(Gh1>;0E#qjIM>X<ChJ%QZ<w$R0IU?IMYia9P&oLcf=1oq>Eh)K!W4<s19^WDj-c7{BZMcW;P(5G^CvZy-m(MYup<ayW%mnyVJ8w4zP'
    '&oNSHWCPpPsvE%tqFYpfIT3A>Lu#deDFny1*xc-F&tq+}OwxF+KQ=IT1N7?I5^MC;?f*!csI9&M8YobW6Os+aH5<eWf=%s?QYv&vxwCmR'
    '^mUP=U^z@v55siVW22WP1we~}{VxQ7-qsyc!~nuh^<K+B0hK^%QdE=(G|u_Y3=jAU5Oe$!g|B&{HTXt`EC*cBWYr}VGNprFTZ%_q1MoF~'
    '7zy?AYycL14V6<mkFRbkhAbglPj-VYVu%W9^r32v)75as4_Fg{w##`{#7T*HjW}wb4f&FPYucgT8LmpUmRfS1-g>3P6+>5Tn+?ll1C8p5'
    'oW<SS7c>V>(twt30PBF#B$D>!Ku>C7)y3pS?r`P)aKu5?eGDBrR}I%`g<I0~7TO5yGcjYw*x`i(2Xhk(87BO+Aw)C<$JKbmX8EUC(^(#p'
    'wv?O$(<N+n+u1iO#%4yyMpX=-klpce#kmY#f4uQ!H72$SZyRk3tJ=WSUFF^@kA=wBFVhs*1f(AS0c|M%`)N}=W{-msYJK9_eK}&%O}Oi%'
    'VK-;9WAw4W^$=^5eGw`wANZDJSq^LibgFQz9hCuPpua43wVTDE8?ss9%KgFOtg3(4)6zB4?T?gf26b;M#0-jS!`YQz_dvaI-OX|LR?4Ph'
    '7QFSq5>;I!2QTN!jcmoHkyr1(rk<A7+C1NPG%M!+o(b0vz1EEDyRI|kH6@Jl0<C}`aG4zj{KEFM>E+&bv#7r195k8uZBhroa26L~aLlqK'
    '^cJ$iQ5lT;0t~VWgHmd)pv5XccDzf1JbQC5COVpV(Ucw*IS*&^c0+I#3%;{ziaQzqvpKcij6kC+=5X-(4Awl>W$k2D5e*K*Yj0ut5nLl|'
    'Vq`(jHAMc(rTmFyEXP*-2h?5hzn`jcUi3-sw`yXn&iHN$UG(PYZDQi@khU+V=bOO?XmTNn!2f(lr&1P(X5t%~q~gaPLL&<;jl*4OW<jgW'
    'Ow3~w#00iX^Vc!B>@nUEdljc8@xBPz8WFfF<r)EQj%dd;r|FzU6gM?3NyR_8$fOwT`NEWRu$tVPk`6$3UYn!mON`2XVQQIU-jzTmj15xb'
    'hUH(H80C<6rbP*2L!_ANJ$x(z8%u@L^*S+$O_6K~YS&hX;?|U00=Y6#6}Gq^nN!d-Fr3sib)>FWqF<EYE0DY=(N{oUpYQ?YF>r~&Xvx_<'
    'u@8$lo;Bw=52tBdBt$*KgMwKcUy}DH;`yIGdIAq3F7jb<amDDhGS?phA5D#5k$Rly+S!#?g&pEmUwpD4ppkjIt@KK24p2w$PYx5j$uD9b'
    'V)jPK7|4lmvoV>lG|R<l#+W?V$HTaZbFYA-UxTJ`fvECWa$nHD`ijyyrg)Wlb2>nThklCJ(D5~g_=#7U3Sdz)ki6~zW52t*>WDE7ec=PY'
    'jlnbqqO3e^tet7sXQ>}jJ`cRe`TaWp&o6FPn~M2#GjMXc*DT0q7(xGQe}^n@I-_hl%T?RmXX1YyYu%TyjC5Kbf{(AyO5M2|LZb?aMM;tW'
    '4Vi=Ax@~Ci3vXa@MR~)k8_J8<<ncaf9AKODyM6d)ybLixsLRz$VEj@CW2qnz2hFB5c__9%-|3~~E?>+(CAg6&dF>?`p*IOl8J_qK$~PJO'
    'p-f7BDBU4R=oS3YDZ#f@6Lv$5C$Uq0JV)?xY?#H!f8u$^+)K!W@{3d14uKl+?4}$c40=U$8O7I;0{Ns}e}}kZ+%s0U)N0>G!%#(tSC(DD'
    'HCp!aRDPTx_p|KfKMF4dmBL@V3=X!CMq6b>MhqdP%KF!&%FEe!NMDcsN%j+7%x;&n?U=0SAYg19@r0OP2J>mc_d+~D0?YTy_{D2!2CE7B'
    '0O&ZS@to%AVu!?d%Sv1c2R`z;3gn?&e_#YuYWx}?4fwipuw0!%8xNnNGN1DXfb<ZEc+-=!FjUaycx{^G$T2foq`b?3<j_4Ar56PQgguiV'
    '@tIc?=eSxy!QU(h<m7d}ZFRwq>pp$sZ_nWnb)%9P_XT;6>V?d`R?X98*mKx}kM(@zWx`|W=*$y*KXLrx^uz1JUj$tKenLD#-v=2r6)yq4'
    '7ViM?6Yu^%>nf?pn+u%z{ra}XAG*oc1G)&i_WO3<D2_hTG;X|_ulP-HRMT6C2eQ7DfBSlPRink4s519}m@hKDo{G3N$Z=bbzh#Y?`JhqA'
    '=@$YIfop(~@&!I1hfeXF`8x;-lyhgvwU%vsn5#baw0)G(Ton%5+)$Gyp<$|Wt}=R?vvcc|b<u!@X=B*e%UnRp=#yN%SKlZohYiZPX&bLy'
    'LA|_D>daI<MQ9p9c3k%4U_G&^MXn>vD`ydF++W;lHQk7<J=5bOj`d8+bCTJu4oS$$n|4-YUe43J4)%`%WZKU&8l6P%Gdmo7tAm;*&>~E|'
    '5x8UxoYBSwH9Sx9jbQJbbT<S0bQ?p;^r*&7j!G?B83qoyQ3`A8Ah&d2<94Mn>iR}sbs1_=sgVB;NYzX_PVO@2s{2|Q;c>%}l2<KTcSo*w'
    'Zqu+WAKM3tL(uvREJyj8eq9u_``ZLx3Yo(zkA(>5{(z;btP2S6r~WC+7Z|Zn>U5Z(@%tk7(xAKnT)N)J>ORb=S494dpC)6Abh_IRI56@f'
    '*;^Z&{1B8hCLT%SFyu)MoB~jkl~%@c8>?J6(RoP0aR2B3{P+K=|H@1$U?gV1aZrCgqtfUE^H`CCEaKu%DFrtM#k>zTa>lP+fVV~p7^TS2'
    '2F~IFEbT6N%Tf`DO3(*|IrGFo5k3<H_u&HV?70UV1pvJ$K-ge3hau_$k`)(;mvVnyn!NY~MGovm3zA>+3<Z4jd`9QpU!!+)PVt5Bpv0G9'
    '3ktZrkNAs7fNq-8Flt$hX@bxu!pBCL^b#~69B1%rG|TfO8}xcOCzW+(PJ6#bZI=H@jI{%{?;Pxs9dbQekZU}H=2J@qHS(F4KX~3LNiNbD'
    '!R8<43s{-TV)9~MrXDN_>ESX02&6+_T*{F!#3$x&lG07B{V^c;U<-_PV?fcE4|Yr^9y*FM4>J~|gTJ?JfZGD1r8wGcD<HMq;ZdgUC0$7G'
    'J&oi1Cq}OgjDZj4EX(ZD!-&n%2EeEcau_(`d{SrcPfwMpH`YYB%dk8%ROFNnD&$;_hbuNP;G|vwmb)2tCwHzfU(jp)B!N>`evWx=tCu&h'
    'C9=c(t(VURWxh8xO>hv0u-D><l57r|3!nfSMFc(a=nCcnn-1ApJEw|GudjguGzeJUg(>vX-ftkrc!HoFe4`VY_5Qs0`0VOgkDClIK~y|B'
    '{U8NF_5nQ14_vOo#_I)tNyFJU-}Lx6JRw`gFIk+%ULfO8(npks#vt@E`NoVtuzv;HNW>1>2U}LqVXI?>9SHO+ID%v4cD`46S45VieQc76'
    'lu4y56?JZ$s?0A#Z>TSBkt3}okWqhZKLNK}Rqv|n99Twd1ZL>~$BbL};|RD1)-KAO8{*szWtkbrtpdT=IejzH0hgZ9ytg&(YUcswd^S9b'
    '^H&&G<S)u@0V!(+Rf{t+G%Vf~_yt@AjZ8{}@ik3-FQa0pab;v=`9$`<&A8bm<1ZGMholaJ;f&IJYh0gi0RACymczhgcWCy!Ke-o}ljsO^'
    'i?oF91?jcik3bzv?851V5^M!*kOgaSLKmzTdb5O^o;)E^UVx;DiyRXJP1p?q9SnLi1+^W3(q1;bdy2tI&KQRUc@_(EBVnc>&MtT`c8{U!'
    'UW-^V?}3%va#_|j<NU@l_{squVmzZ=YkPK<o(VNdr1j#uhACRk&6b~1o?p*cPBEehz$=OWCZKZXi-00S29<1nlli2!kWV&F&APFX1Ix`i'
    'D6l3x|B=MST_b)%rW-n2$(Z))#kJ1j+%>gR>6wJ9Ss^o7CCW=XGp2K7R%SPY%~?%vsFL=KOrUs(iaD}gfL0znva-`Dh98{0L2~{`7lTT2'
    'yEP&5ylqS1$&_y^p_K{hG%&QYG&D1{-AZ6(s=#_+2BemqG6oG6EKw)7Mv<8>MwM0a+m<ia*Uk0P-%;^jCymU(r_Z9iHsy(7Svi^V%0zg='
    '%&Ml$BW_FM-RKIfWAA8dztjwWumws2bxBCOB3~!)?qtrA-7V|p|2hMsuo$nQ7fk_jNBkxly;d`)mAh5kJ$(VAUV>+24q4?ZEgec0t!CPE'
    ')BWxK#mK@t3B74Ha1!at?7IA%N&2frhB@^z#vO2;{<Let#nUQ~XcN#Rn5w}(Y|Oaxi!lk{)X)%BVst0vpT^CSATa4=88LMyYwt9ssdUCT'
    'lUXYpa!0O}y;iHRBo--xQPXF2YV7}D{@TVQyhg6sh*&dQGv%$K)h+Vg>b^^p-wMFD&49~$-60JwFSu7OTq6~(V@(9)sy2t7qo6D@T&<l('
    'wbQ(z07{wa#~#GRsH!jTkB+rfZ-GmVC9o;lC_&JG&FA`TZ#6KC`zJLzePpSCm|vZGC9H`%<&P~jFWPvyLfZ~G)N+B#jHQaHn5K?B(L9A!'
    'c_zh`5DVOz+qiKL)!=uhyq66mGZqhpNo7TABngidRhNFBJgvjMUbELZWHqR+ShrG`gE~|+fOQf=`3@OoT|4jA3}WN)Z|07r$lRYb9@MP3'
    ';SJnV68xuxR4)qZMVM_kHsmpIS#EjmR_=gE$~xKK%!I7A&Fb_->RBarvenw^GFhsN|GMtdXxW%%y1E@QS~kAbw$n)Ns_)gg&E-NR)9pA8'
    'zbx`EaI~@W'
)
FINAL_FILTER = '{ Filter = { Bundles = (\n    "com.apple.corelocation",\n    "com.apple.Maps",\n    "com.google.Maps"\n); }; }\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "Tweak/Tweak.xm")
    if not source.is_file():
        sys.exit(f"Missing source: {source}")

    root = source.parent.parent if source.parent.name == "Tweak" else source.parent
    candidates = [root / "Tweak" / "Relocate.plist", root / "Relocate.plist"]
    existing = [p for p in candidates if p.is_file()]
    if len(existing) != 1:
        sys.exit("Expected exactly one Relocate.plist in Tweak/ or repository root; no changes made")
    injection = existing[0]
    current_filter = injection.read_text(encoding="utf-8")
    if not re.search(r"\bFilter\b", current_filter) or not re.search(r"\bBundles\b", current_filter):
        sys.exit("Unrecognized injection filter; no changes made")
    if re.search(r"\b(Executables|Classes|Mode|CoreFoundationVersion)\b", current_filter):
        sys.exit("Injection plist has extra filter keys; no changes made")

    current_data = source.read_bytes()
    crlf = b"\r\n" in current_data
    normalized = current_data.replace(b"\r\n", b"\n")
    current_hash = digest(normalized)

    target = zlib.decompress(base64.b85decode("".join(FINAL_TWEAK_COMPRESSED_B85)))
    if digest(target) != FINAL_SHA256:
        sys.exit("Embedded source integrity check failed; no changes made")

    if current_hash == FINAL_SHA256:
        print("Final Tweak.xm is already applied")
    elif current_hash == CLEAN_SHA256:
        print("Clean source verified; applying Relocate final 0.1.23")
    else:
        sys.exit("Source is not the expected clean or final Tweak.xm. "
                 "Restore the clean file and remove older patch steps. "
                 f"Found SHA256={current_hash}. No changes made")

    # Write only after all validations. Keep source's original line ending style.
    if current_hash == CLEAN_SHA256:
        source.write_bytes(target.replace(b"\n", b"\r\n") if crlf else target)
    if current_filter != FINAL_FILTER:
        injection.write_text(FINAL_FILTER, encoding="utf-8")
        print(f"Injection filter updated: {injection}")
    print("Relocate final 0.1.23 ready. No diagnostic hooks or logs added.")


if __name__ == "__main__":
    main()
