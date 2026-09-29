# A enciclopédia de speeds do Duck - A lógica das guerras, do sprint, todas as mecânicas importantes, etc

**Origem:** https://forum.tribalwars.com.br/index.php?threads/a-enciclop%C3%A9dia-de-speeds-do-duck-a-l%C3%B3gica-das-guerras-do-sprint-todas-as-mec%C3%A2nicas-importantes-etc.344151/

---

Deixo aqui um tópico com a teoria toda necessária para jogar speed, de forma a serem o mais eficientes e rápidos possível, mas também a jogarem o melhor possível.

ah e já agora, vikings = bárbaros, isto foi escrito para o servidor português

**Comecemos com as "bases"**, e coisas que têm que estar prontas ou a postos na vossa mente antes do speed começar:

Jogar speeds tem uma coisa como "base": recrutar tropas sem parar.

A regra é essa. Podem haver exceções.

Com isso em mente, a vossa probabilidade de ganhar um speed aumenta drasticamente, visto que muita gente nem sequer faz tropas, ou pelo menos não constantemente.

Outra coisa a considerar é que mais aldeias = mais produção de tropas. Em rondas em que conquistar aldeias é uma possibilidade cedo, é isso que deve acontecer, dependendo das circunstâncias (estou a falar de rondas que comecem com mais de tipo 2100 pontos, especialmente com muitas aldeias bárbaras por jogador, como por exemplo [os 4 mosqueteiros.](https://forum.tribos.com.pt/index.php?threads/ronda-speed-os-4-mosqueteiros.144715/)

Duas outras coisas importantes::

-> nunca deixar o armazém encher (ok, tudo bem se tiverem excesso tipo de ferro e deixarem encher de ferro mas o resto não estiver cheio, podem existir situações em que não há problema nenhum isso acontecer, mas a regra é que ter o armazém cheio = perder recursos, portanto, evitar ao máximo)

-> evoluir sempre fazenda antes de precisar dela. isto vai na mesma direção que a "base" inicial, qualquer paragem na produção de tropas é perda de eficiência e uma maior probabilidade de perder a ronda. Vejam o tempo que demora a evoluir a fazenda e vejam o tempo de recrutamento de unidades que vocês têm até à fazenda ficar cheia. O ideal é não arriscar ter que ver isso, e simplesmente evoluir a fazenda antes de ficar cheia... Mas desde que a produção não pare, tudo ok

### **Conceitos e mecânicas principais (algumas destas coisas são um bocado avançadas e específicas, mas convém saber que existem)**​

Utilizarei estes tempos como exemplo para explicar backtimes:

		
		
	

	
		![1749571070082.png](https://forum.tribos.com.pt/index.php?attachments/1749571070082-png.13608/)
	

**Backtime** -> um backtime é o tempo no qual as tropas de um adversário que te ataca retornam à sua aldeia. Alguém a 1min da tua aldeia te ataca, sabes que um minuto depois as tropas estarão de volta na aldeia do teu adversário, portanto, se o atacares a chegar exatamente no segundo em que as tropas adversárias regressam à aldeia, o adversário não tem como desviar as tropas e está morto. Considerando a screenshot acima, imagine-se que sofre um ataque vindo deste jogador, sendo a unidade mais pesada o aríete, e o ataque chega às 15:30:00. O backtime é adicionar o tempo de viagem da unidade ao tempo de chegada do ataque à tua aldeia, ou seja, 15:30:00+00:01:07 = 15:31:07, e esse é o tempo no qual o adversário deve ser atacado para ser dado um backtime com sucesso, e falo disso na secção de scripts abaixo. Existem várias formas de apanhar esse tempo sem se terem que fazer cálculos. Vídeo sobre isso mais detalhadamente-> [aqui.](https://www.youtube.com/watch?v=Uny_MFKfH5I)

**Backtime na mesma unidade** -> Tipicamente, o backtime é dado com unidades diferentes e mais "leves" que a com a qual o jogador original atacou. Por exemplo, se alguém ataca com aríetes, normalmente dá-se o backtime com vikings ou com cavalaria leve, porém é possível dar backtime na mesma unidade, o que pode ser bastante útil quando:

-> não se sabe se o jogador é maioritariamente defesa ou ataque (pode vir um ataque só com cavalaria leve e aríetes e catapultas, e o jogador ser defesa)

-> o jogador tem tribo

-> se imagina que o jogador vá spammar ataques depois, ou até mesmo mandar antibacktimes (explicado abaixo)

A ideia principal é que um backtime na mesma unidade

-> de aríete permite partir a muralha, e minimizar perdas

-> permite mais facilmente dar backtimes a cavalaria leve, visto que a única outra forma de o fazer é mais difícil (ver backtime numa unidade mais lenta)

Como se faz isto?

existem duas formas. A 1. é a ideal, pois a 2. é completamente arruinada se o jogador catapultar a praça de reuniões, porém pode ser mais segura noutras situações.

1. Simplesmente mandar o ataque antes do do adversário bater.

Antes de se receber o ataque ao qual se quer dar backtime, desviam-se as tropas com as quais não se quer atacar o adversário e ataca-se o adversário exatamente no momento em que o ataque bate na nossa aldeia. A ideia é que o ataque envia-se em milissegundos anteriores ao ataque bater na nossa aldeia (imagine-se que o ataque bate aos 400ms, se eu conseguir tirar as tropas da aldeia atacando o meu adversário aos 200ms, acertei o backtime (as tropas voltam sempre a casa de um ataque aos 000ms) e consegui desviar as tropas antes de o adversário me as matar, 200ms depois. Simplesmente se tem uma aba com as tropas todas preparadas para atacar o jogador, e vê-se ou noutra aba ou pela hora do servidor o horário no qual o ataque tem que ser enviado.

Fazer isto é arriscado quando:

-> se tem uma internet fraquita, qualquer lag pode causar delays nisto e oops perdem-se as tropas de ataque em casa

-> o ataque chega tipo aos 200ms ou menos. É super arriscado tentar quando esse é o caso, porque o ataque tem que ser enviado mesmo no segundo em que o ataque chega, e tem-se apenas uma margem de 200ms para o enviar. Se for necessário (se se vir que se perde o jogo se não for feito), faz-se isso, mas idealmente é melhor não.

Este tipo de backtimes causa alguns bugs (os quais não devem parar os jogadores de o fazer)

-> [bug de tropas a viajar no tempo](https://forum.tribalwars.net/index.php?threads/troops-time-travelling.290141/) -> pode acontecer o jogador enviar o backtime a ms posteriores à chegada do ataque do adversário, e mesmo assim... não perder as tropas com as quais ataca de volta e conseguir efetivamente dar o backtime na mesma

-> [bug de multiplicação e tropas negativas](https://forum.tribalwars.net/index.php?threads/duplication-bug.289362/) -> pode acontecer o adversário ter um relatório em que mata as tropas todas com que o jogador dá backtime na mesma unidade, mas o jogador consegue dar o backtime na mesma (e nem faz sentido as tropas morrerem, visto que o ataque é enviado em ms anteriores, ainda à uns dias me aconteceu isso), fazendo com que o jogador fique com tropas negativas em casa (tem que ser atacado ANTES DAS TROPAS REGRESSAREM para deixar de ter as tropas negativas ou então vai ficar com 0 tropas quando estas regressarem á aldeia, vejam o tópico linkado). Este bug é problemático para o jogador que ataca, pois perde tropas a limpar o adversário sendo que não sequer devia de perder nada porque o adversário já não tem aquelas tropas em casa.

2. Fazer isto por "snipe"

"Snipa-se" por cancelamento o ataque a chegar, deixa-se uma aba aberta com a quantidade exata de tropas que se "snipou" (as tropas têm que regressar a casa no mesmo segundo em que chega o ataque, se não seria apenas um desvio normal).

Isto é útil nas situações em que o modelo anterior não é:

-> quando se tem quase uma certeza de que o ataque não vem com catapultas na praça de reuniões (se fosse o caso, não se conseguiria atacar depois porque esta teria que ser reconstruída)

-> quando o ataque a chegar bate em milissegundos cedo (por exemplo aos 100 - seria arriscado usar o método acima, mas não é problemático de todo "snipar" este ataque porque depois têm-se outros 900ms para enviar o ataque, pois basta que seja enviado no mesmo segundo)

Portanto, basicamente, abrem-se duas abas a atacar com todas as unidades com que se quer dar o backtime (o resto desvia-se, normalmente mandando um ataque para longe do outro lado do mapa)

A primeira usa-se para snipar o ataque, fazendo com que as tropas regressem á aldeia depois do ataque bater na aldeia. A segunda usa-se para enviar o ataque, assim que as tropas estão de volta á aldeia, ainda no mesmo segundo do ataque do adversário ter batido na aldeia.

Para tentar não levar backtime na mesma unidade, deve-se enviar o ataque real em milissegundos cedo e forçar o jogador a dar backtime pelo método número 2, visto que é mais difícil de executar e é efetivamente nulificado mandando catapultas na praça de reuniões, mas no geral, enviar vários fakes é chato o suficiente e em principio garantirá que o adversário não vai adivinhar qual dos ataques é real.

**Backtime numa unidade mais lenta** -> É também possível e útil dar-se um backtime numa unidade mais lenta do que a unidade que vem a chegar.

Tome-se, novamente, por exemplo a screenshot que está no início desta secção. Imagine-se que alguém manda um ataque de vikings, a chegar, novamente, às 15:00:00. Sabemos que o backtime será às 15:00:40. Podemos, ainda antes do ataque bater na aldeia, mandar um ataque de aríetes para dar o backtime, se se for rápido o suficiente a ter o backtime calculado.

O mesmo pode ser feito, por exemplo, com nobres a um ataque de aríete. Ou com vikings a um ataque de cls (mas é mais difícil, por exemplo na situação acima, o jogador tem 4 segundos para descobrir o backtime e o mandar, visto que as cls voltam a casa 44s depois de serem enviadas para atacar (22+22), e o ataque de vikings demora 40s a chegar ao adversário - para dar backtime a cls é mesmo ideal ser com a mesma unidade).

Isto é fácil de se prevenir, com fakes. Um jogador provavelmente não irá perder tempo a dar backtime a todos os fakes que lhe forem enviados numa unidade mais pesada, só porque podem ser reais.

É algo a ter em consideração e pode ser bastante útil.
