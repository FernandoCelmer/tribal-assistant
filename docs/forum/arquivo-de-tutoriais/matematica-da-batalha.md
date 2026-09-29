# matemática da batalha

**Origem:** https://forum.tribalwars.com.br/index.php?threads/matem%C3%A1tica-da-batalha.17718/

---

Como se calcula quantas tropas irão morrer em uma batalha?  
Primeiro você precisa saber  
  
(AA) ataque do tipo arqueiro = soma do ataque de cada unidade do tipo arqueiro vezes a sua própria quantidade.  
Exemplo: vou atacar com 10 arqueiros e 1 arqueiro a cavalo.   
Então AA = 15*10+120*1=270.  
(AC) ataque do tipo cavalaria = soma do ataque de cada unidade do tipo cavalaria vezes a sua própria quantidade.  
(AG) ataque do tipo geral = soma do ataque de cada unidade do tipo geral vezes a sua própria quantidade.  
(AT) Ataque total = AA + AC + AG  
(DG) Defesa do tipo geral = soma da defesa geral de cada unidade vezes a sua própria quantidade vezes o bônus 1 da muralha + o bônus2 da muralha  
Exemplo: tenho na defesa 10 lanceiros e 10 espadachins  
Então DG = (10*15+10*50)*bônus1 + bônus2  
(DC) Defesa do tipo cavalaria = soma da defesa cavalaria de cada unidade vezes a sua própria quantidade vezes o bônus1 da muralha + o bônus2 da muralha  
(DA) Defesa do tipo arqueiro = soma da defesa arqueiro de cada unidade vezes a sua própria quantidade vezes o bônus1 da muralha + o bônus2 da muralha  
  
Porcentagem de perdas das tropas de ataque com ataque tipo geral:  
((DG/AT) elevado a 3/2) vezes 100  
Porcentagem de perdas das tropas de ataque com ataque tipo cavalaria:  
((DC/AT) elevado a 3/2) vezes 100  
Porcentagem de perdas das tropas de ataque com ataque tipo arqueiro:  
((DA/AT) elevado a 3/2) vezes 100  
  
Porcentagem de perdas na tropa de defesa:  
(((AC/DC)+(AG/DG)+(AA/DA))elevado a 3/2) vezes 100 vezes x  
  
X é um numero que eu ainda não sei calcular que depende da proporção dos tipos que a tropa de ataque tem, se o ataque tiver só um tipo de ataque, x vale 1. Esse x sempre é um valor próximo de 1 então não faz muita diferença.  
  
Muralha  
Nível Bonus1 bonos2  
0 ___1.00 ___20  
1 ___1.04 ___70   
2 ___1.08 ___120  
3 ___1.12 ___170  
4 ___1.16 ___220  
5 ___1.20 ___270  
6 ___1.24 ___320  
7 ___1.29 ___370  
8 ___1.34 ___420  
9 ___1.39 ___470  
10 __1.44 ___520  
11 __1.49 ___570  
12 __1.55 ___620  
13 __1.60 ___670  
14 __1.66 ___720  
15 __1.72 ___770  
16 __1.79 ___820  
17 __1.85 ___870  
18 __1.92 ___920  
19 __1.99 ___970  
20 __2.07 ___1020  
  
Vou dar uns exemplos de como usar a formula  
1000 bárbaros + 1000 cavalaria leve + 1000 arqueiros a cavalo contra 1000 lanceiros + 1000 espadachins + muralha nível 20  
  
AA = 120*1000 = 120 000  
AC = 130*1000 = 130 000  
AG = 40*1000 = 40 000  
AT = 40 000 + 130 000 + 120 000 = 290 000  
  
DG = (15*1000 + 50*1000)*2.07 + 1020 = 135 570  
DC = (45*1000 + 15*1000)*2.07 + 1020 = 125 220  
DA = (20*1000 + 40*1000)*2.07 + 1020 = 125 220  
  
Porcentagem de perdas das tropas de ataque com ataque tipo geral:  
((135 570/290 000) elevado a 3/2) vezes 100 = 31,9%  
  
Porcentagem de perdas das tropas de ataque com ataque tipo cavalaria:  
((125 220/290 000) elevado a 3/2) vezes 100 = 28,3%  
  
Porcentagem de perdas das tropas de ataque com ataque tipo cavalaria:  
((125 220/290 000) elevado a 3/2) vezes 100 = 28,3%  
  
As perdas da defesa serão de 100%, porque (((AC/DC)+(AG/DG)+(AA/DA)) é maior que 1  
  
  
Agora vamos fazer 625 bárbaros contra 1000 espadachins + muralha nível 0  
  
AG = 40*625 = 25 000  
AT = 25 000  
  
DG = 50*1000 + 20 = 50 000 nem vou somar os + 20 porque eles não vão fazer diferença  
  
Porcentagem de perdas das tropas de ataque com ataque tipo geral:  
((50 000/25 000) elevado a 3/2) vezes 100  
((2) elevado a 3/2) vezes 100  
(Raiz de 8) vezes 100 = 282% mas como a perda máxima é 100% a perda da tropa de ataque vai ser 100%  
  
Porcentagem de perdas na tropa de defesa:  
(((AC/DC)+(AG/DG)+(AA/DA))elevado a 3/2) vezes 100 vezes x   
AC = 0, AA =0, e com só tem um tipo de tropa de ataque (só tem tipo geral)x =1.  
((0+(25 000/50 000) + 0) elevado a 3/2) vezes 100 vezes 1  
(raiz de (1/2*1/2*1/2)) vezes 100 = 35,3%  
  
Agora o ultimo exemplo: 5000 bárbaros + 1000 arqueiros a cavalo contra 10000 espadachins muralha nível 0  
  
AG = 40*5000 = 200 000  
AA = 120*1000 = 120 000  
DG = 50*10000 = 500 000  
DA = 40*10000 = 400 000  
  
As perdas da tropa de ataque valem 100%  
  
Porcentagem de perdas na tropa de defesa:  
(((AC/DC)+(AG/DG)+(AA/DA))elevado a 3/2) vezes 100 vezes x  
(( 0 + 200 000/500 000 + 120 000/400 000)elevado a 3/2) vezes 100 vezes x  
((0.4 + 0.3) elevado a 3/2) vezes 100 vezes x  
(Raiz de (0.7*0.7*0.7)) vezes 100 vezes x  
58,5% vezes x  
Se você usar o simulador vai ver que a perda real foi de 5883, ou seja, 58,8%.  
Esse erro é devido o x não ser igual a 1, ele não é igual a 1 porque tem + de um tipo de tropa no ataque.

## Página 2

Fiz alguns testes no simulador vi como se comportava e pronto, mas não foi muito fácil  
  
  
Não tem uma defesa ideal para todas as situações, mas eu faço assim  
Pra ataque tendo + de 213 aríetes e sendo recrutado tanto no quartel como no estábulo (cavalaria leve e arqueiros a cavalo) acho que já esta bom  
Pra defesa ai vai depender  
se tiver tempo pode ser na proporção 1 : 1 : 1 ou algo parecido como 3 Lan 4Esp 3 Arq  
se não tiver pode ser só recrutar lanceiros e cavalaria pesada mesmo  
  
mas na verdade eu tinha vários tipos de aldeias dependendo de quais recursos tinham sobrando na aldeia, de onde a aldeia esta, de como meu inimigo se comporta e coisas do tipo  
  
tem um tópico antigo meu sobre defesa balanceada  
http://forum.tribalwars.com.br/showthread.php?t=12034

## Página 3

Paladino é tipo Cavalaria

## Página 4

Complicada essa matematica toda ai,  
prefiro usar o simulador e ver no que vai dar  
mesmo assim, excelente tutorial!
