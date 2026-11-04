#!/usr/bin/env python3
"""Relocate rootless 0.1.22 consolidated production patch.

Applies the tested behavioral modifications of 0.1.16, 0.1.17 and 0.1.22
onto the exact clean Tweak.xm source provided with the project. Diagnostics
015/018/019/020/021 are intentionally removed. Never run older patches.

Safety: refuses modified/unknown source rather than overwrite work.
"""
import base64
import hashlib
from pathlib import Path
import sys
import zlib

SOURCE_SHA256 = "56b6aad7a222eb382fbb2b74b509b0c10ba671c2ebedc1f7e9cb7781c0c40883"
TARGET_DATA = (
    "c-q}O?RMKXvj6oIuzJ#!97mF~o82C{ZtU1e>#gnNMt0jhs@8`VAqh1_atYFolFfVEfA{Pg?jzh8e2@T0O0unH@3}drwTO?wU@(|3"
    "0P_`_$5E1!Zzn<IrJdP#jjwdc<;jmM?TY_f<^Pp=N&4|9N@%zEX|*__@r<(W53k-ObV3svjwv@AG%xO`chi|Qi<0-JN2k%)OIZ}2"
    "d7(F@$uSM+)Jv(`>@f6#XgWyQ_~vI8`q3RWXnf_<2@5HCcX~3oxO#VZ@dG(%c5l6;``fkn6R_*9AKy&7ESyB$Iqifrrm5FSXn^C="
    "PQZ8yfGniRc3gbyH5%7Z6p$nszYe|Yfckr~U>Zc%UQktb9)16Aph~<r&YQ3>CF3jsxapx$EZQNGC*iFZFkKQNl(WdE>U%B;bP}?Z"
    "L9>t8Rn|}o(r?j%BboLZN2i*&M^TjcEQAR^KPKb+W3O>OIA&vP;Ux>Q9jNA5w%4elI@$KzBEaGRW=4~VH>Tu#aGnJLX}wnjZa1E_"
    "ptcSF{p1B14Ee0}>h0UpHsY#E4ru5jka--?IS@zSPyxvSMLsnM{7Yz>B_ZkUH9j{=!0k2@FW^+PlS6j91SZ+r{Y#&`r;~*88KIL2"
    "1%ljCf;_;9mlAKBW?n#$-!(mf<S7s=jsO?lK{yvP2913mfN<cTu{WMkpV(}5ix_coH=`jL&@^S?l#?`?P6JWO0*dUy2~WKRfhE4B"
    "0`z%ACRlfuuoU=_unF-Qzaa*b5-*_ymUIliIRj?c!CFoem`6GjbGc<vCO`wzH}DS|liP^-iUMl>h%Rqod0UZAH9a3(usJ=!b%tq>"
    "z~kxBjE--}K2jbV9`Hpto+VL;tVvo!fUEX28AEeE(h%{V11<#4+9$*F!Mh~FDV)G=1*G%eqYekArt`}<g>HK}7$8Lp`#v)e`j+%M"
    "e|*taYhJW9Q4R&$7RZ>J0BI}8fbCdN0GLDxX`K%SX#xueGQvw|Kyz|1%v%UDNcl65u3^o(r|dcbs9l2%s-#dX#L!L^ASK8i0xt(="
    "k-j|Ru^0NxhkkMmj4D6>`7=vrM-i+SF#Oxe8^EQH1Q_jEaB)3`1vtik1QGFea)j&Ow?Rvu7?H2PCV7X>ILbgqen)yP!uZczn7qqg"
    "so8Y`TE;H^+$jG-RJU@FWp+V10x}o4E<v*7Er$n9CApg;=)~hF^!Y_J0KGL%qojYp)vs1AgxVtuo0oOa@(v@?xAcvLlhiRTPT!l_"
    "XhWE}FfIHX^=F|N(*zWpi(;YkHiVxA&_d4Cx)x?asaDfYXzh(sPD8Aqn=%oK{ivnNbr$*oJvo+J@s;=jHe{jvIqIkeK5RrbVZfX("
    "`yeWsCam*pehn4dKn1iP091k7FdvGGKe(^oM9JJs`+}fXPY$j$QFn;OW;8P4qu55VK9|6UdYq+{W3rPX9uQ3R>X;QkpPnI@#gb*5"
    "zP+VM!o*-|M}pL7sg3Z@f0CABI4G4k?UUVh+g20hCePar?DMyKH98@rAJSa+J8GdC_-@<c4+p^g)<bu!Sr7_Fjle<@WX*v!ljguj"
    "wHi?vjJVJiuyus{OKW@>voJ)PxEU-$7K|H!)dj=Jan~D1w1ojqVWc$kmxC9ico_I7oYue>%qk3c1ddZ!x*z-~gH5Kl18~j|(OSPt"
    "F))~jXAI0f;Gx2_=VYGo6y%+-U)e3HV=p9;=5|1@)!XT{I|UobT@T2cy8;kXPD##D+Ao2Yx(~DpZHb2bD2V}es+p_QO?Lx#mBA{u"
    "{w}5k&8oecGw+7Bfao2ANINh>XcibEK^g*|g)iVZ9);oBXgmeE1r{*aS?MCCZ9W4-+dol7wuNliyW37XLt?1Lun)m}8qcmGsJ}`H"
    "{<(;5sG7J{-TFGO-64N3NLU)gG`YP1sB17u*?WWze|xP~?6abb@{?@H!eM&aD(FtO+f$lq772B6-)^E;S5ZkW1K=h1CycHebaa`-"
    "0XfIy3{>>0fgZA{H_WP5hUSG1HSL?0d2Ap!tnEMyrcy-y+%PFP92&HcYXQCjOQjjD*|uLWc4_>+{*l+rqJ(_}6Wj|9$Kx#V#*2PV"
    "!g5{S4X6PeSJla_X%zb{OE@hW%I|{lVoLpfFaJiL3|M6z7d`SK(P&h|LT|k5grURYpRQt-KRxgL|7MRua&DeYc6;^QVAQE)-(6#&"
    "QBR^cMi*@4tnm-j^Mx&IFR?C`w9K1{7(nO+U<GBM2AKL(i><yoAAsJwPT8WO>|;gQ+?$3JCan=Dw}7E(eXXZR1ywl{<~=n<kRL3f"
    "2x92~$AEzxeXm`1Y&3EK(K#5A9&iUOLMql2G~2m#06IY4kOrPx3rme516BKC&*efrZC6GG4D_L@>}zNv6=P$58ynieHB<Z83Pg7k"
    "VWlh<p#j;oBKFiSw)vJeFTlj#%FPbjRTu59ly>9Ta#(zcaKZ@9@m|rZk;ihtI8jY8jx)46#tZZWVYh%Sbp0FHU$4V#jtdkemOL1O"
    "bv7Y#Qfl^n1t#D5?&NhlLmsN4?Y2hfQ!zVLRG#;6s9XCgYQDmI4eZhSKJzaHMj8#?Z`-r07{LXSw<rU1LSrU}R7(Fs2###Ax!KuX"
    "M7hZ_NuqiFv4Oc8pjXe9Sfj6Q|9jFzZ}kn(K!d8CkZLfh*dU(oZ)$fGQlU+Xoh`yDXIYAZ<uFOS1-Kn|Bcqok1we~}{VxSTzOCD)"
    "hyjG1>b-`60xE&Tq^K;BXk3V&98U@|5Od-ag|8VJ?|(y5F9GuPg`nZ(C6zKo#4-|$mG{Bd0Aj?{OL-qG{0b^3bPkT-Jqc|I*=n*I"
    "bdf`pNRuDER5)EVCxL)9k!ZV|S4Nx^m{*9S*7-mz`M0JW`kmpb@U_&E>-1JDC7~EPdfRMRE*of+L;DtYZ(q|CI4K9TbOTr?9VU@-"
    "Uk>zSPOPdJ{m>n**dLBKD7%k=Bj?I7`&{7`biIc*Li<e4*fDlQVc)^r#NxAzv3=SQA~^*|<#@zq`KMmfSsqeuDLE%EOW5qbv#(c-"
    "^^CxWWelH@-O+NzxeQ)!wDDy%CbkN18*K}#%D~h^<=z{Q1<2R0lLXiVq@MTzZK(MBX;VCAkAo6wed5`D1!Brgc<7{IH}lys`dHw4"
    "$hF~LgbK?Cz9(6h1KR+dN?dD4Wk4C^UlzOC&7!~!*{pEoerIu3*1zj%=?dxgdrCHgy7v`g2E}v3*_B_9K)rU|&2jfu%BExHzw^Kn"
    ")m;<^FXzgQY{j~fSMR^No|e^GKi~J1XY>EegsX>MYsS@G*O~H~5=MK0RzMKA%nk#7VSC#2a__rYbl+kQIhn+rGY7z67G;5d%y=Al"
    "3)SJM2*!N@23dtcAvIUfVih1e-lag|VfrJO=xFAJQ+k-CBAhMS4Zu~*#LlWHZgcTxb85XFfm&D0;o$WdtbVMU%E{^?>K_Jo-h#WA"
    "0X8wRq~{tUf8|pC#5hZ_mG}X5x8m=oa-0`^lE<x@9IHKgm_nDm1$vv9_<N-7E9#BS-~%+dmPO!yzNb?q3uH6-4NVgH<9DHvg;tKk"
    "LuqC~E6q&KV-v&#woKBq2we6E@5#K0l7e_&glx44Jd|>^05?apW17-r&O(ZtniixIpF(6(4EB6sN;+6g9!*IHpgXV4(epJ%Wxp`B"
    "%rPHIAQQ$0squlOUz!-jkPoIs0b)a>nCE-=SOzwh3a7huViKDo*%H+5tPsV$DY*o4X`(u8@i;OkplM(@rE984U9CjFD8W}C`ADL#"
    "fWAKAeJWz$3WMR2vwLD67708n&U2njlPHUceyjrpvnaYDmnZU(P=53T9z>L-gY5d2(K~IfKLI|P8o?s{gvqtDOK*?b#4EoGW4=#A"
    "^LAU|l~f#{4lhp*<2Ya{_916)l#GC!2$zq@ge5$crx_!%wU38!6X#xmK)(V_;{s9XN!7ljfBCJIb4>9j@#eIT2oJ^yg(>2-aQPFj"
    "GG)M`W*~Xp1IAuwchwPN5{#t}{4N617>Kg+w6SugoiR(s0TuJWi=5xT2k_$JX1S@HPltn()45}QI>QM1UwS)adD9tX(^;z9?!J)!"
    "Yg_BSgk_Y|`UHIZ{H)ZSyCF2nkXRUJ>EDn!dMHV18vG&}m|RiZ@ahEW1~YlOPihC)CcRD%{_XBng3z~=m%#X?3dT}FAP<^NY4SvF"
    "eX-LE$(_Hed;Xl@Mxx}*i#eemVwx~K@$DDakfShI0Q-!gbce)&mx<SF1RrTk*avF7t(%JDIfAe30v;j%`Qn^%?!{z6#l<PUL!c(a"
    "TRX-Gf#1!-n=rZyHOObJ>N~`3<DRj;rB?ZZ5{AkGyt3>HuHmvLZ0h42xu5aZ|H!-mREoIu-#=&~jhaP7Mh>B*%KF!&ip$w}NMDWq"
    "3I7Q%X19vjwoO)a5HL25e2XY9gN<n{_Chp40;`9R_$6v7ht&jq0Cb$vXin2)u|p!fWhJkK10Q)E4f0T}KQIC+HE|7)`eI!LSfS3K"
    "jfZdA*jVrefb<Xuz5^pr8Uz~J9Is826gg%_vqW_1lN7qAvh+G*fUsxsqZjOmi}J8QekLyeOXSpbzHNQMPw2k<#^0X9A^JuoG42bB"
    "9_0&}dyR@Wkg(^lhZyVS%FBeu%F&s}_z>av)#=sQ;V%-dc!(fhv+je80<hohlV^YINQnfW-|mA@>}aVdnoFF;{rXmpKXmJ<Ub+ao"
    "_Ih^TFbY4?B&xldulY@KR2$%xt_{GyEmdF0zx{l8U6YG7S!M14IbUS@d@AzRpulZC{#G^S`{-IBm%k8r0$c-(lrHckDs+nGY`lY@"
    "KsmRUTx;3J7k>I<FSn04O?6?vB@8uX5*nte;3}iHIXkybTNgE0m^Oxez03uqjXuTId)1BnVpzYJTW;gEN~jk%N}ZYNrwDZ;sE*5?"
    "9IPicbCK%^^U_(w8uu6X8g(~fE6?=Ah@*Ta#W~6BUWX)P<xM*)GOy-oUI+U}1~TpE84XXuOKyjQ?{!d92U>=yHv*Tefiv2;poZsh"
    "x)JQ1lkR$8pYCHwnI6@s&QYmEi(}wW7^Seb4suHeHf~oMqpolCm6xFsl@j?MfK<h#qxd0nF1xR#5uVl@DS73xb$8@?=QcIl@~M5G"
    "H~_8Bz;aa2a@R#6cYo{PD<N}u>#+dgJRY!8l~n-&@n$$-=>j7bTAdDJG=5)2Ug8%wfD70ASl@>^^|Ek06Q{}8BAM>i1P+WWD)!a}"
    "CqDosjTsD*C<w&sXr}-aWvP|%+{P-GPIMYjFx>zBKmYwN{a=xC0gOZr90&CmGpdYEFpo7k$Rf)AkWg@A<g-m^F0NhR8_f(x$vE1;"
    "Jj%e*?vQsZk%6cfeNdRQ$S@M(GeK}4uF=k(d%#f%zVY-CHW<x8fVzP2>^k-m;jb%`7oVW0fxU1+Qq0PuMo(vS-uX3rPv;b$%JvI<"
    "8MdH+%Vj8DL;`fvoQ6@0V$3&!HW5BH;>t_N0pU3PU&C3N#=PI{;+%B)iaG868n#&a2RYUb*uHbHOLoZJY(ehu3|dSrmefdRUb^+N"
    "U65SnLxIgdNEfg&rNtD*qD((nlG4Lv1Q1AvV|gh@!H}QgA+3~ddhL$^!L243?Z$wzu^8-_PCRrJXCA)VPWpdu*#NgCL`!kBT2?@6"
    "yDg$jog2DP-g^>7=}(N_85jc}%o*o)>0!v`XaitW2008IaWSd$%hOYB>Wy+DJY-mrVkUG-`z3NN$HNsH7;w_B0E^uWyHhyVn0VwY"
    "f07`mt3F2}NzUsJuqF6m`p!#d{UR%ro+dbm1K4X(NC}^V<^m|dMj=6uJiLXuz@|gC&Ye@urgwKh0qXlK?Z6beN%uDpV<OW?7rxPn"
    "<lR3lKEAkp(G?~GOb``MO0Se4;8);bUJ1Dh8?WpCISFRpeA5-<h_p>yT(UTgJYU73l#i$mjX~&f^~OxRRDT28NX8CY2Td#J&}>^_"
    "2Le4af#68HotHX+gG{%wk4?DDy;8_hS?9*7ibNIk10Bm-<Vb4;WY`<oPr&U~<-6*6G94o}0<(00W9lCKaRl50YZs=@4RPUyGH%9k"
    "%Rn%8PTx-QfJ@hC-ffOLx$^*XJ|CP%=^KnIiWg<~fW+%TRpN{c4U2aRet}RyLz5CgbVrl1$Eh4@R2mssK32W&GcLbj;>F_fkkp|+"
    "m{FQGM^*m1_=m(<4g<4hq1khJ@+dGT;SuN-WeGhB(wW+iKpi$wi-r<x1#FN7Yj8pbtQY!W2{%1^MwGk&NfTu$Nin(C2Ld`6^kxET"
    "+Xtn+Y<iCrgKoB_Er$ic;<Gmr6l@80!Gp0!3|;kF#FBYiRtmgj>6?u68_VD;26%$;j8>)X*<N}kR4b9zi|ZPuXfZciekyr>H)AQq"
    "h$a9pWe}Ty%AGHKiVW$O(t=IqlgdId*(fpV%$zQ6`Z9?%zUawuao0$kkmU`Xtz=Al_2OD*aqgPhIk`;2RjiPi^$z8wonp^9GAq&~"
    "!R9RINo#5k*aV7)sF-8u6=>!D*H)S<&G7y6w@A((>7rlClC>s8kpOB5Je50YCA1>bRSpd8tQ?w|BWoqFBIj5&FauJ<P8p+9C+U-0"
    "qsYt`qsvNJFpHP#>*jjF<TbK~lSby?(`Q*;nexQ2telivMMf=YW|ebq5x1rBZghp#v3In!Un+(_Xo8YJT@uiaO#BDDJDIb1w`tw{"
    "UuR$x7Na%vqA5Tgh~FefuTjrw#cq{%PhY{PH{cnWLzej}mktGsmQ(hb8IeTn_s>Q;&q?4-dEd#%snT?cb0+1lW*pPkaV8vakw>v("
    "!o|}nkZ2RoB$%qfK5XQ|`Nfz7aB5(PDmi+`&J~s8W=Rm3^s>}?c_(Y{)aJW$#yD5$?`o3Jt(68dS7C7^bB&^==T&O#|6n4_+H9Ui"
    "(#nunGg~uvrl!?B5@_aqmuAtFfbW}1Q}lX3K21^ZsHB=kPEE&}@X2ju3OYwYS!B3fJ0D}aenSD2BGr#Qh>KBKUp^ikYpdP^mkLW@"
    "Q?${7paz@I)!E)EU>NsLDs=kLQUQ^;I`u|c6Awy6S!iCg@luVp9dfAT0+$&J6;m=z9ebjF3RNi-Oa7IWC2HMmT)T%V@LQhJaV?v>"
    "ic?XTlvcDtl89JQdFe%Z%`)!Qn!U;)t3Y+dx)s74)S;#UtdkVV56H6V+Ijb85F3yGFn26P=JBktRk7lRH}FVF@K*(?S`<`^Fxzmf"
    "$z$NM+~=i9P=y1cDC=Z@Gc%joHmlPUsb`hgSxYOci>#wA{_DC+!)0Td>FRdKaM}1)+jcFv%f46pK9>u%Ot<4W;<Cv90&ByEfB"
)

def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "Tweak/Tweak.xm")
    if not path.is_file():
        sys.exit(f"Cannot find source: {path}")
    data = path.read_bytes()
    crlf = b"\r\n" in data
    normalized = data.replace(b"\r\n", b"\n")
    current = hashlib.sha256(normalized).hexdigest()
    target = zlib.decompress(base64.b85decode("".join(TARGET_DATA)))
    target_hash = hashlib.sha256(target).hexdigest()
    if current == target_hash:
        print("Already consolidated. No changes made.")
        return
    if current != SOURCE_SHA256:
        sys.exit("Source does not match clean Tweak.xm expected by this patch. "
                 "Remove previous patch steps, restore the clean source, "
                 "and retry. Refusing to overwrite unknown code. "
                 f"Found SHA256={current}")
    if crlf:
        target = target.replace(b"\n", b"\r\n")
    path.write_bytes(target)
    print("Relocate consolidated 0.1.22 applied:", path)

if __name__ == "__main__":
    main()
