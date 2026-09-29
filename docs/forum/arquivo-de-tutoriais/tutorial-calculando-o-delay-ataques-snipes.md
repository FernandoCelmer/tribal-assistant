# [Tutorial] Calculando o Delay - Ataques & Snipes

**Origem:** https://forum.tribalwars.com.br/index.php?threads/tutorial-calculando-o-delay-ataques-snipes.274133/

---

**[Tutorial] Calculando o Delay**  
  
**Delay** é o termo técnico usado para designar o **retardo** de sinais em [circuitos ](http://pt.wikipedia.org/wiki/Circuito_eletr%C3%B4nico)eletrônicos, geralmente o atraso de [som](http://pt.wikipedia.org/wiki/Som) nas transmissões via [satélite](http://pt.wikipedia.org/wiki/Sat%C3%A9lite_artificial).  
  
O valor do delay incomoda mas não é o problema. O problema é a variação do delay no meio do jogo. A velocidade do jogo mudar várias vezes em momentos aleatórios atrapalha demais.  
Tempo de atraso de um sinal, em [reverberação](http://pt.wikipedia.org/wiki/Reverbera%C3%A7%C3%A3o), [eco](http://pt.wikipedia.org/wiki/Eco), ou em equipamentos eletrônicos em geral.  
  
Eu estarei dando dicas sobre um mito chamado Delay que para muitos é uma dor de cabeça, é importante também saber o tempo do seu delay, até porque ele pode ser variável, alguns jogadores nem precisam saber o tempo de delay constantemente por terem uma internet ótima e por isso ele não varia tanto, mas para quem não tem a internet boa é importante ter o conhecimento do seu delay e das variações que ele pode ter.  
**  
ERROS COMETIDOS AO CALCULAR O DELAY:  
  
_Sem perceber muitos contam como delay o atraso do relógio do servidor do tribal wars que normalmente atrasa 1 segundo, e alguns contam este segundo como delay e outros mal sabem que o relógio é atrasado e por isso erram em grande maioria os comandos.  
  
Outro motivo de gerar erros ao enviar os comando é também justamente este citado anteriormente, pois o servidor vai mostrar apenas o segundo inteiro mas ele pode estar atrasado por exemplo em 1.5 segundos (1500ms), ou seja o comando será enviado 500ms depois do normal (0.5 segundos quase 1 segundo) e dependendo do seu delay caso ele for de 500ms, o comando pode sofrer uma atraso de 2 segundos e acaba que você erra e sai achando que ainda o problema foi com o tal do delay, mas o erro foi seu !  
  
Uma dica é olhar pelo relógio do windows, atualize-o e no momento certo do envio do ataque envie-o, ou seja o momento em que o relógio do windows marcar o momento exato de envio pode enviar o comando que dificilmente você vai errar :]  
  
Exemplos:  
  
_**_Se seu delay for de 400ms, e tiver de enviar um ataque as 00:00:01 então você tem de enviar o ataque a partir das**00:00:00:600ms**(Tem de ter muita pratica, pratique, o segredo de tudo é a pratica).  
  
Usando o ultimo exemplo, se você conta como delay o atraso do relógio do tw, então você teria de enviar o comando 1 segundo antes (**23:59:59:600ms**) olhando pelo relógio do tw, não aconselho enviar pelo relógio do tw, sendo que cada pagina pode gerar um tempo de atraso maior ou menor. Como exemplo é só você abrir varias paginas, vai notar que a diferença vai poder variar e se você não perceber vai enviar o comando no momento errado !_  
  
**FORMAS DE CALCULO DO DELAY**  
  
Há varias formas de obter uma média do seu delay, executando testes online e outro é pelo CMD.  
  
  
**1 - Sites que medem a velocidade do seu ping e da internet:**  
  
1.1- <http://www.testeseuping.com.br/> >> Site que envia 5 pacotes a um host teste e da uma média (Este vai dar o resultado apenas do ultimo pacote enviado, então é bom olhar o valor de todos)  
  


![1242791.png](http://www.testeseuping.com.br/resultado/1242791.png)

  
  
1.2 - <http://pingtest.net/> >> Faz alguns testes na sua conexão e da um resultado final do seu ping.  
  
[![](http://www.pingtest.net/result/80407787.png)](http://www.pingtest.net)  
  
1.3 - <http://www.speedtest.net/>  
  
[![](http://www.speedtest.net/result/2671124504.png)](http://www.speedtest.net)  
  
**2 - Usando o Prompt de Comando,**   
  
2.1 - Vá no menu iniciar -> Procure por **cmd** ou**Prompt de Comando  
  
**2.2**-** Quando abrir a janela do cmd ou prompt de comando, digite: ping [b](http://www.tribalwars.com.br)r48.tribalwars.com.br   
  


![375072_608715339156149_1041943386_n.jpg](https://fbcdn-sphotos-c-a.akamaihd.net/hphotos-ak-frc1/375072_608715339156149_1041943386_n.jpg)

  
  
2.3 - Após digitar o comando ping e respectivamente um endereço host do tw, vai aparecer algumas informações, a ultima linha por exemplo mostra o tempo de resposta mínimo, máximo e **médio**. Ou seja, 1s (segundo) = 1000 ms (milissegundos). Então como podem ver no meu resultado, a média foi de 288ms, mas é importante ver não somente a média mas também o tempo de resposta dos 4 pacotes.  
  
**Detalhe é importante você ver os 4 pacotes enviados e não somente a média !**  
  


![392482_608715372489479_1702882985_n.jpg](https://fbcdn-sphotos-d-a.akamaihd.net/hphotos-ak-frc1/392482_608715372489479_1702882985_n.jpg)

  
  
_OBS: Você pode testar com qualquer outro endereço, mas é melhor usar o do tw,**ou usar o host de algum mundo como exemplo: br48.tribalwars.com.br é ainda melhor.**_  
  
É isso aí pessoal, é só colocar em pratica e treinar a arte que é snipar ou de enviar ataques em tempos pré definidos xD, espero ter ajudado !  
  
**Att: Alex - SnittraM**

## Página 2

Já dei uma olhada, e isso não é só aqui como é com todo mundo que eu perguntei, você ataca com o relogio do tw e quer se basear com o horário de brasilia?  
1 segundo é 1 segundo cara, vai dizer q 1 segundo do tw é diferente de onde marca 1 segundo com relação ao horário de brasília.  
A única pessoa que eu já vi cancelar nts no mesmo segundo foi o vingador, por exemplo , ele tomando nt:  
00:10:00:258  
00:10:00:298  
00:10:00:358  
00:10:00:398  
  
Ele enviava o atk das 00:10:00:340 ( por exemplo)  
e ai quando ele ia cancelar era exatamente quando o contador batia em 5minutos.  
e saia exatamente certo o snip, mas isso ai que eu já presenciei apenas ele, tudo depende da internet, não tem essa de relógio do jogo tá errado, se tu ta usando ele pra atacar e cancelar atks tem que se basear com ele, todo mundo cancela um atk com 1 ou mais seg , por exemplo pra snipar, quando tá no horaroi de snipar um atk, nunca vi alguem mandar o snip no segundo exato e ainda conseguir, do fato de o atk do cara chegar as   
10:25:48:296 e o outro as 10:25:48:500  
e vc vai la e solta o horário exatamente no segundo q tem q enviar e o apoio chega as 10:25:48, sem se importar com os MS, bem difícil que caia no msm segundo, a net tem q ser mto boa.

## Página 3

Então você tá me dizendo que demora de 1 a 2s pra enviar um ataque e sua internet segundo essa img acima faz download de 7mb/s então sua net deve ser superior a 10 MB e ainda demora 1 a 2 segundos pro ataque ser enviando '-' , legal, minha internet é de 1MB moro no Maranhão e dificilmente passo mais de 1 segundo pra enviar um ataque quando minha internet está normal mando até em menor tempo, sem sofrer alterações por fatores externos que reduzem a velocidade da internet obvio, ou quando meu delay tá normal também.  
  
O tempo de carregamento de uma pagina nem sempre influencia no tempo de resposta de um comando '-', as vezes o comando pode ter ido mas a pagina carrega além do esperado, normal.  
  
Aqui passa 1 a no máximo 3 segundos pra pagina terminar o carregamento no normal da minha net e meu ataque demora em média a partir de 500ms a 1.5 segundos para ser enviado dependendo da velocidade dela, mas o ataque foi independente do tempo final de carregamento da pagina, se o delay marcou no momento de envio um atraso de 1 segundo ele vai a 1 segundo, se marcou 1.5 segundos o delay eu mando a 1.5s antes vai depender do momento, aqui costuma varias mas o normal é de 500ms a no máximo 1.5s, por isso é importante ficar testando minutos antes de enviar um ataque ou coisa do tipo para se ter uma base antes de enviar de fato os ataques, apoios e cancelar ataques..  
  
Também testei utilizando o site que tu usou aí e como dito meu ping é sempre o mesmo, em qualquer site que uso é sempre variando de 250 a 400, resta saber o tempo de resposta do servidor do tw e no que ele pode interferir, e os motivos de muitos ataques ultrapassarem a faixa de 1 segundos no envio dos comandos.   
  
[![](http://www.speedtest.net/result/2671124504.png)](http://www.speedtest.net/)  
  
  
\-------  
  
**#TÓPICO ATUALIZADO, VOU ESTAR ATUALIZANDO, BUSCANDO MOSTRAR DA MELHOR FORMA POSSÍVEL A FORMA DE DESCOBRIR O DELAY, AINDA NÃO SÃO CONCRETOS ESTES RESULTADOS !**
