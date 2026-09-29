# [Tutorial] Saber calcular o tempo de ataque / apoio

**Origem:** https://forum.tribalwars.com.br/index.php?threads/tutorial-saber-calcular-o-tempo-de-ataque-apoio.26421/

---

Bom, primeiramente gostaria de dizer que estou muito feliz de estar postando meu primeiro tutorial, não sei se será importante mas achei no minimo interessante....  
Pesquisei se havia algo do tipo no fórum já, porém não achei nada. (me desculpem se não epsquisei direito, mas tenho quase certeza que não tem nada igual)  
  
Vamos parar com as baboseiras e começar o tutorial certo!!!  
  
Primeiramente, você sabe qual a importância de calcular a distância de uma aldeia com outra? Muito simples, é importante para saber se você conseguirá apoio ou se seu inimgo conseguirá apoio de uma(ou mais) perto de ti, assim podendo se preparar estratégicamente para o ataque ou defesa.  
  
Colocarei aqui a tabela de tempo que uma unidade demorá para atravessar uma distância 1|0:  
  


![3307567278_bf7dd5fbaa_o.jpg](http://farm4.static.flickr.com/3330/3307567278_bf7dd5fbaa_o.jpg)

  
  
Com isso teremos uma base para fazer os calculos.  
É mais simples do que muitos imaginam o calculo de disntância no TW.  
  
Para calcular uma distância agente tem que fazer o delta de disntância. (diferença)  
  
Com isso teremos: delta distância igual à x1 ou y1 - x2 ou y2.  
Onde:  
**x1:** coordernadas de sua aldeia.  
**y1:** coordernadas de sua aldeia.  
**x2:** coordernadas da aldeia alvo.  
**x2:** coordernadas da aldeia alvo.  
  
Ex.: João tem uma aldeia de coordenada 000|000 e quer saber a distância de sua aldeia com a aldeia de coordenadas 001|000, com a unidade mais lenta sendo a calavaria pesada (usairei sempre ela pelo tempo ser 10 mins).  
  
**Calculo:**  
  
Delta X = 000 - 001 = -001 (sempre usará números possitivos, mesmo se der negativo)  
Desta Y = 000 - 000 = 000  
  
Ou seja, João andará uma distância de 1 campo, por não ter movimento no Y.  
  
Com isso João usará a fórmula: Tu x S = Tt  
  
**Onde:**  
**Tu:** Tempo da unidade  
**S:** Distância (Campo)  
**Tt:** Tempo total  
  
Então o tempo total será: 10 x 1 = Tt Tt = 10  
O tempo será de 10 minutos.  
  
**Simples não? Mas e a distância em diagonal? Como faço?**  
Simples, usará o Teorema de Pitágoras.  
  


![3307602196_a1ee4ddf19.jpg](http://farm4.static.flickr.com/3381/3307602196_a1ee4ddf19.jpg)

  
  
Onde:  
**Dx:** Cateto 1 será o eixo X (delta x)  
**Dy:** Cateto 2 será o eixo Y (delta y)  
**H:** Hipotenusa será o campo (distância) percorrida.  
  
Como todos (ou a maioria) sabe, a fórmula é (C1)² + (C2)² = (H)², mas modificarei para o TW, que ficará: **(Dx)² + (Dy)² = (S)²**  
  
**Ex.:** João ´tem uma aldeia de coordenadas 000|000 e quer atacar uma aldeia de coordenadas 003|004 com a unidade mais lenta sendo a Cavalaria Pensada, assim João irá demorar:  
  
Delta x: 000 - 003 = 3 **(lembrando que não haverá negativo)**  
Delta y: 000 - 004 = 4  
  
(3)² + (4)² = (S)²  
(S)² = 9 + 16  
(S)² = 25  
**S = 5**  
  
Com isso saberemos que João terá uma distancia de 5 campos.  
  
Calculo para o tempo: Tu x S = Tt 10 x 5 = Tt **Tt = 50**  
João irá demorar 50 minutos para chegar ao seu destino.  
  
Se o número der mais que 60, você deverá dividir o mesmo por 60, aonde o número inteiro será hora e o npumero quebrado será o minuto, mas faça a regra de três que estará embaixo.  
  
Se o tempo desse 90 minutos, fariamos o seguinte:  
  
90 / 60 = 1.5  
Sabemos que irá demorar 1 hora, mas e esse 0.5??!!!  
  
Simples, faremos uma regra de três, aonde 60 equivale a uma hora, então 0.5 horas equivalem a X minutos.  
  
60 - 1  
x - 0.5  
  
30 = x  
  
Assim saberemos que o tempo será de 1 hora, 30 minutos.  
Agora se o minuto der quebrado, você deverá fazer mais uma vez a regra de 3 para ver quantos segundos irá demorar. _(apenas com números depois da vírgula)_  
  
Bom, espero ter ajudado e qualquer dúvida postem aqui que afrei o máximo para ajudá-los.![;\)](https://cdn.jsdelivr.net/joypixels/assets/8.0/png/unicode/64/1f609.png)
