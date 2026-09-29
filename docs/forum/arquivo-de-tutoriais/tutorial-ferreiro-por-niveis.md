# [Tutorial] - Ferreiro por Níveis

**Origem:** https://forum.tribalwars.com.br/index.php?threads/tutorial-ferreiro-por-n%C3%ADveis.167381/

---

Olá!  
  
O intuito desde é explanar o sistema de ferreiro por níveis. Peço que qualquer duvida/informação adicional seja postada para atualizarmos e mantermos este mais completo.  
  
Primeiramente segue uma tabela com as unidades e suas diferenças em cada nível.  
  


![dwxamr.jpg](http://i51.tinypic.com/dwxamr.jpg)

  
  
  
A maioria das unidades recebem uma diferença significativa na força de combate frente os aprimoramentos no ferreiro.  
  
_Exploradores:_  
  
Caso sobrevivam exploradores suficientes e o explorador foi pesquisado no ferreiro, edifícios, recursos e unidades serão visualizados conforme o nível de pesquisa.  
Nível 1) Apenas Recursos   
Nível 2) Recursos e edifícios  
Nível 3) Recursos, edifícios e unidades ( também sendo possível visualizar as que estiverem fora da aldeia )  
  
Obs: alguns mundos com ferreiro por nível utilizam uma formula diferente para os ferreiros, onde os mesmos somente são evoluídos até o nível 1. Para mais detalhes sobre exploradores, ir a [Este Tópico.](http://forum.tribalwars.com.br/showthread.php?t=20932)  
  
_Maquinas de Guerra (catapultas e arietes):_  
  
Level 1: Possibilidade de se criar as tropas.  
Level 2: Aumento do "poder" em combate de 25%  
Level 3: Aumento do "poder" em combate de 40%  
  
Alguns pontos necessário:  
  
**-** Você pode realizar até 15 pesquisas por aldeia.  
  
**-** As pesquisas de lança nível 1, e espadachim nível 1 não são revogáveis (são pesquisadas automaticamente assim que os requisitos mínimos forem alcançados)  
  
**-** Caso revogue uma pesquisa, não receberá os recursos novamente.  
  
**-** Ao fazer uma pesquisa, ou revogar a mesma TODAS as unidades serão influenciadas.  
_Ex: Caso produza 500 lanças com pesquisa nível um, pesquise o nível 2 e produza mais 500 lanças, as 1000 unidades serão consideradas como nível 2._  
  
**-** As pesquisas são "adicionadas a aldeia", caso seu ferreiro seja catapultado, as pesquisas vão se manter.   
_Ou seja: as alterações de níveis de pesquisa são executadas somente pelo titular, através do ferreiro pesquisando ou revogando._  
  
**-** Caso pesquise alguma tropa, produza a mesma e depois revogue a pesquisa, as tropas serão consideradas nível 1.  
_Ex: Pesquiso catapultas, recruto 250 catapultas e revogo a pesquisa. Minha catapultas serão consideradas nível 1._  
  
**\- Os níveis de pesquisa serão SEMPRE considerados da aldeia onde as tropas se ENCONTRAM**  
_Ex: Detenho de uma pesquisa de lanceiros nível 3, e serei apoiado por uma amigo com 1000 lanceiros, não importa o level dos lanceiros do mesmo, assim que chegarem em minha aldeia serão considerados nível 3. Ou seja as tropas sempre serão influenciadas pela aldeia onde estão localizadas._  
  
Estou adicionando uma configuração usada em vários servidores para esse tipo de ferreiro. Adiciono que o intuito desde é explanar o funcionamento para auxiliar os jogadores que desconhecem do mesmo. Logo para discussões sobre estratégias e afins, seria interessante um novo tópico.  
  
Atenção, essa não é necessariamente a maneira mais efetiva de distribuir as pesquisas, ou ainda é bem relativo de acordo com a estratégia de cada jogador. Sugestões postem aqui ou me enviem via mp, vendo a funcionalidade estarei atualizando.  
  
\- É interessante padronizar as pesquisas defensivas, para poder efetivar sempre as mesmas.  
  
\- Nas aldeias ofensivas **SEMPRE** deixe pesquisas para tropas defensivas. Você vai ser atacado e as tropas pesquisadas podem dar uma diferença de até 40% nos valores (por isso o intuito de padronizar a defesa, para efetivar o uso das tropas).  
_Ex: Aldeia ofensiva: Bárbaros nível 3, cavalaria leve nível 3, arietes nível 3, espada/lança nível 1 (minimo em todas as aldeias), + 4 níveis defensivos, seguindo seu padrão de aldeias defensivas. (é possível deixar lanças e espadas nível 3, ou ainda lanças nível 2, espadas nível 2 e outra tropa defensiva nível 2)_  
  
\- Evite usar níveis de ferreiros para exploradores em aldeias ofensivas.  
  
\- É possível obter um padrão defensivo para a tribo inteira, aumentando assim a eficácia do apoio entre os membros.  
  
  
Modelos de Pesquisas. (créditos _Johnny Tapia_)  
  
Ataque:  
  


Código: 
    
    
    [B]CONFIG #01[/B]
    
    Lanceiros: 3
    Espadachim: 3
    Bárbaros: 3
    Espiões: 0
    Cavalaria Leve: 3
    Cavalaria Pesada: 0
    Aríete: 3
    Catapulta: 0
    
    Total de pesquisas: 15
    
    [B]CONFIG #02[/B]
    
    Lanceiros: 3
    Espadachim: 3
    Bárbaros: 2
    Espiões: 0
    Cavalaria Leve: 2
    Cavalaria Pesada: 3
    Aríete: 2
    Catapulta: 0
    
    Total de pesquisas: 15
    
    [B]CONFIG #03[/B]
    
    Lanceiros: 3
    Espadachim: 3
    Bárbaros: 2
    Espiões: 0
    Cavalaria Leve: 3
    Cavalaria Pesada: 2
    Aríete: 2
    Catapulta: 1
    
    Total de pesquisas: 15
    
    [B]CONFIG #04[/B]
    
    Lanceiros: 3
    Espadachim: 3
    Bárbaros: 2
    Espiões: 0
    Cavalaria Leve: 2
    Cavalaria Pesada: 2
    Aríete: 1
    Catapulta: 2
    
    Total de pesquisas: 15

Defesa:  
  


Código: 
    
    
    CONFIG #01
    
    Lanceiros: 3
    Espadachim: 3
    Bárbaros: 0
    Espiões: 0
    Cavalaria Leve: 0
    Cavalaria Pesada: 3
    Aríete: 0
    Catapulta: 3
    
    Total de pesquisas: 12
    
    [B]CONFIG #02[/B]
    
    Lanceiros: 3
    Espadachim: 3
    Bárbaros: 0
    Espiões: 3
    Cavalaria Leve: 0
    Cavalaria Pesada: 3
    Aríete: 0
    Catapulta: 3
    
    Total de pesquisas: 15

[/QUOTE]  
  
[Tática "Openeye" (créditos ao _dominaria_ por compartilhar)](http://forum.tribalwars.com.br/showpost.php?p=2010225&postcount=19)  
  
  
O tópico será alterado conforme necessidade/caso apareçam outras duvidas pertinentes ao assunto.  
  
Att, Goht

## Página 2

@ Dominaria: Bom, da pra se ver algumas vantages nisto Dominaria.   
  
Porém, será que realmente compensa??? Pois para fazer CP será utilizado muito mais recursos, além do tempo de recrutamento ser bem maior... Ou seja, para se refazer tais tropas se gastaria muito mais em muito mais tempo, além da já dita perda ofensiva. Além disso ela é mais lenta, os farms demorariam muito mais, sem contar que a capacidade de carga diminui em 30.  
  
Será que vale mesmo?  
  
@ Tapia: Não gostei das suas configurações ofensivas, diminui por demais as forças ofensivas, como jogar com barbaros nivel 2 não me parece uma boa estrategia, ainda mais tendo em vista que sempre jogamos com 5-7k de barbaros...  
  
As defensivas estão boas.

## Página 3

**Sempre usei arco + espada, por ser a mais completa mas claro que nao existe defesa perfeita. Tava refletindo sobre o openeye e pensei em fazer isso em mundo de ferreiro simples tambem, acho que daria certo. Sempre tive um pulga atras da orelha sobre a existencia de cavalarias pesadas, pq sempre tive na cabeça que elas so serviam pra apoio rapido, mas agora to pensando diferente.  
  
To pensando pra caramba em como seria cav. pes. no speed, dps posto num topico.  
**  
^o)
