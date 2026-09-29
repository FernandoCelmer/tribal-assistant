# Tutorial: Mandar fakes em Massa, NT fake

**Origem:** https://forum.tribalwars.com.br/index.php?threads/tutorial-mandar-fakes-em-massa-nt-fake.330619/

---

Esse tutorial foi uma adaptação do Tutorial do Paulinhorj do Chrome, porém para Opera.  
  
  
  
  
\- Esse tutorial é para mandar fakes de várias aldeias mais rápido e mais fácil.  
\- Esse Tutorial vou ensinar a mandar NT fake com mais facilidade e rapidez.  
  
  
  
  
  
  
  
  
Começando~  
  
  
  
  
1) Baixe o Opera na ultima versão, nesse link [http://www.opera.com/pt-br  
](http://www.opera.com/pt-br<br />)  
  
  
2) Faça a instalação como qualquer outro programa.  
  
  
3) Execute o Opera, Aperte **Alt + P**. vai na parte de **Navegador** , e habilite a opção **Habilitar a opção de atalhos avançados**.  


![wzzTi5i.png](http://i.imgur.com/wzzTi5i.png)

  
  
  
4) Instale esse Add-ons para o Opera <https://addons.opera.com/pt/extensions/details/linkclump/?display=en>  
  
  
5) Aperte **Ctrl + Shift + E** , (Gerenciar Extensões), vai na parte do LinkClump e vai em Opções, em **Actions** Delete a config existente, aperte **Add Action** e configure dessa forma e coloque em **Save**.  


![zcPWeji.png](http://i.imgur.com/zcPWeji.png)

  
  
  
6) Adicionar Scripts na barra de ferramenta do Tribal Wars.  
A) 

Código: 
    
    
    javascript:$.getScript('https://dl.dropbox.com/u/72485850/tribalwarsbrasil/link_praca.js');void(0);

Atalho de Teclado: 3.  
  
  
B) 

Código: 
    
    
    javascript:doc=document;if(window.frames.length>0)doc=window.main.document;url=document.URL;if(url.indexOf('try=confirm')>1){doc.forms[0].troop_confirm_go.click();} doc.forms[0].attack.click();

Atalho do Teclado: 2.  
  
  
C) 

Código: 
    
    
    javascript: 
    var coords_ataque='457|534'; 
    
    
    var lanca =0; 
    var espada=0; 
    var barbaro=0;
    var arqueiro=0;
    var explorador=1; 
    var cavalaria_leve=0;
    var cavalaria_arqueira=0;
    var cavalaria_pesada=0; 
    var ariete=0;
    var catapulta=1;
    var nobre=0;
    var paladino =0;
    
    
    /* a lista de tropas pode ser substituida por :
    selectAllUnits(true);
    */
    
    
    var cookieName = "farmeruk";
    var aviso = false;
    var repetir_ataques = 1;
    var parcial = true;
    
    
    
    
    var campos = 0;
    var ignorar_aviso_campos = true; /* se quiser ser avisado caso a coordenada esteja fora do campo definido coloque essa variável como false */
    
    
    
    
    
    
    
    
    $.getScript('https://dl.dropboxusercontent.com/u/72485850/tribalwarsbrasil/saquear_aldeia_farmar%202.0.js');

  
  
Atalho do Teclado: 1.   
(OBS: Esse Script pode ser mudado, ele será o Script de fakes)  
  
  
  
  
  
  
  
  
**Está configurado todo sistema, agora vamos colocar em prática, na próxima parte ~~~~~**  
  
  
  
  
Depois de configurado, agora vamos seguir essa parte para executar.  
  
  
**FULL FAKE**  
  
  
  
  
1) Vai em **visualizações** -> **Combinado** , selecione o grupo de aldeias que irá mandar Os Fakes.  
  
  
2) Aperte o botão do Teclado, **3**.  
  
  
3) Segure **Ctrl** e arraste com o mouse sobre as aldeias que irá mandar fakes.  


![7e20Tbw.png](http://i.imgur.com/7e20Tbw.png)

  
  
  
4) Irá abrir várias abas no Opera, selecione a Ultima aba, e aperte o botão **1** , até chegar na primeira aba,  
  
  
5) Após isso, você irá apertar o Botão **2** , até chegar na ultima aba,   
  
  
6) Volte para parte 4 e seguidamente parte 5 do tutorial.   
  
  
**VÁRIOS FAKES NO DACING**  
  
  
  
  
**NT FAKE**  
  
  
1) Abrá os 4 Comandos de Ataque na parte de confirmar comando,  
  
  
2) Abrá 2 Abas brancas antes do NTFAKE,   
  
  
3) Abrá 1 Aba após a ultima aba do NTFAKE, e deixe selecionado a **URL**  
Dessa forma,  


![DFptjH2.png](http://i.imgur.com/DFptjH2.png)

  
  
  
4) Agora selecione a primeira ABA, e segure o botão do Teclado 2.  
  
  
Se fizer corretamente, seu nt fake irá ficar 100 ms,  
  
  
_OBS: Internet Lenta, Pc lento, irá influenciar Drasticamente o resultado dessa Etapa. aconselho desligar seus downloads e tubos vermelhos._  
  
  
  
  
  
Atenciosamente Remberto,
