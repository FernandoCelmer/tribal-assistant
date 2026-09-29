# Tutorial - NT de 300ms - Google Chrome

**Origem:** https://forum.tribalwars.com.br/index.php?threads/tutorial-nt-de-300ms-google-chrome.322496/

---

Boa noite, galera.  
  
Depois da nova atualização do Tribal Wars, os NTs enviados pelo Opera ficaram impossíveis de ser enviados em 300 Milissegundos.  
  
Com isso, procurei uma forma de fazê-lo pelo Google Chrome, que é o navegador mais rápido para se jogar atualmente.  
Segue tutorial:  
  
Step 1:  
Baixe, instale e ative a extensão **_Shortcut Manager no Google Chrome.  
_**  
[LINK Shortcut Manager](http://www.baixaki.com.br/download/shortcut-manager.htm)  
  
  
Step 2:  
Entre nas configurações da Extensão.  


![DgmIJp6.png](http://i.imgur.com/DgmIJp6.png)

  
  
  
Step 3:  
No canto **Esquerdo Alto** , aperte em **Add a New Shortcut  
**Na criação desta Shortcut, insira os dados:  
Shortcut Key: Digite "6", ou outra letra/número/símbolo de sua preferência.  
URL Patterns: ***tribalwars***  
Em Action, selecione a opção "**Execute Javascript"  
**Deixe a parte 1 deste campo em branco.  
Na parte (2) Then execute Javascript below (optional) , insira:  


Código: 
    
    
    javascript:doc=document;if(window.frames.length>0)doc=window.main.document;url=document.URL;if(url.indexOf('try=confirm')>1){doc.forms[0].troop_confirm_go.click();} doc.forms[0].attack.click();

Em Description: TTrain  
Clique em Save.  
  
Step 4:  
Clique novamente em **Add a New Shortcut  
**Em Shortcut Key, coloque a MESMA LETRA/SÍMBOLO/NÚMERO utilizado anteriormente.  
URL Patterns: Deixe como está  
Em Action, clique a opção **Browser action,** e selecione**: SELECT THE RIGHT TAB.  
**  
  
Está feito. Caso você utilize cliques rápidos alternados para enviar NTs, repita estes processos selecionando outra letra. Exemplo: Eu envio apertando, rapidamente, os números 6-7-6-7 seguidamente. Mas 90% dos usuários enviam segurando apenas uma tecla (no caso do Opera, era a tecla T).  
  
  
Qualquer dúvida, só comentar.  
  
Resultado:  


![shAmMoF.png](http://i.imgur.com/shAmMoF.png)

  
  
  
PS: O script é um simples comando de "ok", não se enquadrando em nenhuma regra que o proíba, já que não executa mais de um comando por vez e não automatiza comandos.  
  
Abraços,  
  
  
Rafael Lott []s

## Página 2

eu fiz segurando apareceu essa msg, vou ve aqui de novo.  
  
deu certo! ;D  
  
é pq so funfa onde ta selecionadp, caso não esteja aparece aquela msg   
  
melhor ainda hehe

## Página 3

ói ó,o cara pansando tudo as manhas...vai parar Rafa? de jogar?  
  
E mano,da pra fazer com qualquer script? tipo ali no lugar do script de nt,eu coloco outro...,eai?  
  
Bom tutorial cara,parceirao divulgando tudo ai ![;\)](https://cdn.jsdelivr.net/joypixels/assets/8.0/png/unicode/64/1f609.png)  
  
exite um script que manda nt de 100ms,mas eé ilegal..o teu jeito é legal pelo q vejo,por ser como o opera
