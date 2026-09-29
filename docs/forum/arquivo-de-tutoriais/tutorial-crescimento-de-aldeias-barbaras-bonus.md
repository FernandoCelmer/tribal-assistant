# Tutoriais[Tutorial] - crescimento de aldeias bárbaras/bônus

**Origem:** https://forum.tribalwars.com.br/index.php?threads/tutorial-crescimento-de-aldeias-b%C3%A1rbaras-b%C3%B4nus.202974/

---

Com base na experiência de jogo em diversos mundos e em pesquisa realizada através de posts obtidos aqui e no server .net, venho postar alguns dados relativos ao funcionamento das aldeias bárbaras.  
  
Irei fazer uma lista das informações obtidas de início com suas respectivas fontes e após irei formular uma linha de raciocínio com estas informações no intento de melhor definir o funcionamento das aldeias bárbaras, fundamentando ao final com todas as fontes usadas para este tutorial.  
  
Gostaria de observar que as informações expostas **não só foram aprovadas no Server americanoi (.net)** , _como não sofreram nenhuma represália da innogames_ , **pelo contrário, um membro da innogames chegou a até mesmo comentar em uma das discussões sobre o assunto****(** como pode ser visto através do comentário do Morthy – innogames community manager em**[ Barbarian/Bonus villages evolution formula](http://forum.tribalwars.net/showthread.php?t=250066))** visto serem conclusões obtidas pelos jogadores.  
  
_________________________________________________________________________________  
_  
Minha contribuição:  
  
\- Aldeias bárbaras/bônus **não usam recursos para por ordens de construção**.  
  
\- A variante utilizada (qualquer que seja ela) torna o crescimento destas aldeias aleatórios, entretanto uma base limite é utilizada para definir-se um teto e uma base limite para o crescimento destas aldeias .  
  
\- Cada mundo tem uma fórmula própria de crescimento para suas aldeias bárbaras, mas esta não está vinculada com a velocidade do mundo.  
  
\- Aldeias bárbaras não geram tropas (Duhhh, mas alguns novatos podem não conhecer este fato), mas uma aldeia abandonada por um jogador irá manter as tropas criadas enquanto pertencia ao jogador.  
  
__________________________________________________________________________________  
  
Pouca coisa, agora vamos as contribuições obtidas de forma externa:  
  
  
\- Barbaria_rise formula  
  
Existe uma formula denomidada:  
  
A tradução será simplificada e não literal.  
  
Texto original:  
  
_________________________  
  
  
This means, that since there are 1440 minutes in a day, you can expect a given barb to upgrade 2.88 buildings per day (on w54).  
  
If you heard of the barbarians on w41 (known for outgrowing purple predator over the first days), th barbarian_rise setting was set to .01, causing 14.4 upgrades per day.  
  
Now, barbarian villages do need to have the farmspace to upgrade a building, but I am not certain if they need the normally required warehouse space. They do though need all prerequisite buildings (for example, a barb will never build an academy without 20 HQ 20 smithy 10 market).  
  
_________________________  
  
  
Esta variante ao que tudo indica trabalha com rotações de chances por minuto.  
O jogo a cada minuto rola um percentual de chance de x/1000 ou seja, a cada minuto o jogo testa o valor do percentual de 0.001 a 1, se o valor da chance rolada for igual ao valor configurado no mundo a aldeia irá jogar um edifício em ordem aleatória de construção.  
  
Por exemplo, um mundo configurado em 0.002, faz com que a cada minuto, cada aldeia bárbara/bônus do jogo tenha 2 chances em 1000 de criar um edifício.  
  
Em uma contagem de 1440 minutos por dia, em regra uma aldeia bárbara/bônus cresce 2,88 edifícios por dia.  
  
Ao que parece o mundo 41 do .net, por erro, configurou errado o barbarian_rise colocando a formula em 0.1, o que fez um crescimento de 14,4 edifícios por dia naquele mundo.  
  
Bárbaras/bônus precisam de espaço na fazenda para construir suas edificações (**discordo neste ponto, acredito que haja exceções**), mas ao que tudo indica não precisam de espaço no armazém para construção, afinal de contas, aldeias bárbaras/bônus não utilizam recursos para construir.  
  
Fonte:  
  
[ Barbs when Attacked or Left Alone](http://forum.tribalwars.net/showthread.php?t=226223&highlight=barbarian_rise)  
  
E  
  
[interface de configuração do Server inglês 54](http://en54.tribalwars.net/interface.php?func=get_config).  
  
  
Aldeias bárbaras usam ordem de construção?  
  
Sim. De maneira normal  
  
\-   
Community manager  
  
Fonte:  
  
[ Barbarian/Bonus villages evolution formula](http://forum.tribalwars.net/showthread.php?t=250066)  
  
  
  
Conclusões:  
  
1° - aldeias bárbaras/bônus não usam recursos para construir.  
  
2° - aldeias bárbaras/bônus colocam construções em ordem normal no edifício principal.  
  
3° - Aldeias bárbaras/bônus não geram tropas.  
  
4° - aldeias bárbaras/bônus crescem de acordo com a fórmula barbarian_rise, explicada acima.  
  
5° - Aldeias bárbaras/bônus **respeitam a regra da fazenda**.  
  
6° - Aldeias bárbaras/bônus **não respeitam os limites do armazém**.  
  
7° – Aparentemente o “barbarian_rise” de cada mundo fica normalmente em 0.003  
Fonte: [ Barbarian Villages Growth Rate ](http://forum.tribalwars.net/showthread.php?t=210833&highlight=barbarian_rise)  
  
8° - O limite de cada mundo é definido pelo e barbarian_max_points (no Br41 é 1500 por exemplo).  
  
  
Fatos que ainda desconheço:  
  
1° - Existe alguma preferência de construção dependendo para as aldeias? Algum método de forçar uma bárbara/bônus a construir edifícios específicos que me interessam?  
  
2 ° - Bárbaras/bônus tem tempo de construção independente do ed. principal? Esta é uma dúvida que perdura em muitos posts e mundos.  
  
  
Dentre outras que não me vem à cabeça agora.  
  
  
Controvérsia mais discutida:  
  
**Exceção ao limite da fazenda** Aldeias bárbaras que continuam à evoluir construindo edifícios diversos mesmo depois de terem suas fazendas catapultadas para 1 (segundo relato de alguns jogadores).  
  
  
  
Lista de todas as fontes utilizadas para este tutorial:  
  
  
[Barb village growth speed](http://forum.tribalwars.net/showthread.php?t=171585&highlight=barbarian_rise)  
  
[ Barbs when Attacked or Left Alone ](http://forum.tribalwars.net/showthread.php?t=226223&highlight=barbarian_rise)  
  
[ Barbarian/Bonus villages evolution formula ](http://forum.tribalwars.net/showthread.php?t=250066)  
  
[ Barbarian growth formula ](http://forum.tribalwars.net/showthread.php?t=209316)  
  
[ Farm Shaping ](http://forum.tribalwars.net/showthread.php?t=249724&highlight=barbarian)  
  
[Settings do M54 inglês](http://en54.tribalwars.net/interface.php?func=get_config)
