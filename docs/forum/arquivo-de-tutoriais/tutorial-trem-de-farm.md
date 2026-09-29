# Tutorial Trem de Farm

**Origem:** https://forum.tribalwars.com.br/index.php?threads/tutorial-trem-de-farm.339193/

---

Bom...vamos começar com uma leve intro...este método passou muito tempo nas sombras...os jogadores que os conhecem não gostavam de ensiná-lo por aí, por medo de perderem a vantagem ou mesmo crashar os servidores...mas acho que estamos no br 101 já né? Sem mais segredos  
  
**O método se baseia em pegar os links de "ataque novamente com as mesmas tropas" de seus farms, abrir todos eles de uma vez só e depois enviar um "trem" para mandar todos os comandos de uma vez**  
  
Então vamos por partes: a primeira coisa que vocês vão precisar é de uma pasta específica para os relatórios dos seus farms...vamos chamá-la de FARMS. Criem uma pasta, e passe os relatórios dos últimos ataques que vocês fizeram aos seus farm para lá  
  
Feito isso, utilizaremos um script autorizado para extrair os links de "ataque novamente com as mesmas tropas" de todos os relatórios da sua pasta.  
  


Spoiler: Código do BRE

javascript:  
(window.TwCheese && TwCheese.tryUseTool('BRE'))  
|| $.ajax('<https://cheesasaurus.github.io/twcheese/launch/BRE.js?>'  
+~~((new Date())/3e5),{cache:1});void 0;

  
_Ele deve ser usado quando você estiver na página da pasta FARMS configurado para apenas mostrar os relatórios de ataque._  
  
Assim, ao acionar o script, clique em "export repeat-attack links" para abrir uma caixinha e mais três opções...selecione a opção "plain links" e depois clique no botão "copy to clipboard" para já dar um ctrl + c em todos os links.  
  
_Pronto...você já tem todos os links em mãos...mas como abrir todos eles de uma vez?_  
  
Tem vários meios, você pode escolher qual você preferir. Mas vamos com um site que faz isso e possui a opção de abrir todos os links com um pequeno delay, para que os servidores do tw (que andam muito fraquinhos) não sobrecarreguem.  
  


[ https://standaloneinstaller.com/online-tools/multiple-url-opener ](https://standaloneinstaller.com/online-tools/multiple-url-opener)

  
Copie os links na caixa, ajuste o delay em "Open each URL after X seconds", e depois clique em "open" para abrir todos. Tenha a noção de quantas guias seu computador e internet conseguem sustentar abertas  
  
_Agora chegou na parte derradeira...você tem 50 abas de confirmação abertas. Como você vai mandar seus ataques? bom, mais uma vez, tem várias formas._  
  
A mais direta seria mandar um **Ctrl + Tab e ir clicando enter**...uma forma clássica era por meio do antigo **T train do Opera** (com uma configuração para que mandasse os comandos com mais de 200 ms de delay, para não ser barrado pelo limite de comandos por segundo), mas a versão do Opera que faz isso não funciona mais. Uma forma 100 por cento oficial de se fazer isso seria por meio da extensão oficial **"Tribal Wars Train"** , mas ela tem o problema de que você só pode mandar 5 ataques por clique. Mas existe uma extensão que faz exatamente o que o antigo Opera fazia, e ela se chama **"AutoControl Shortcut Manager"**...porém já aviso que ela não é tão fácil de mexer, principalmente porque tá em inglês. Mas dando uma pista rápida...procure por SWITCH TO RIGHT TAB (mover para a guia do lado) e por SYNTHESIZE INPUT para escolher a tecla que você quer que "automatize", que seria a tecla Enter. **Mas lembre-se, não usem esta extensão para nenhum fim que não seja o de simular o trem que era mandado pelo Opera antigo.**
