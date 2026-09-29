# Tutorial Fxutility para farm

**Origem:** https://forum.tribalwars.com.br/index.php?threads/tutorial-fxutility-para-farm.339194/

---

Abram <http://www.fxutility.net/fake_eng.php>  
  
O primeiro box é onde você vai colocar **um texto qualquer** com as coordenadas que você está farmando ou pretende farmar  
  
Depois selecione as tropas e as quantidades, e clique em **"create"** para gerar o **script de fake** , _que pode muito bem ser usado para farmar_...cole o código na sua barra de acesso rápido e, para usá-lo, basta estar na praça de reunião  
  
_Para pegar as coordenadas das aldeias_ , tem várias formas...tu pode usar este script aqui 

Spoiler: Código

javascript: var win=(window.frames.length>0)?window.main:window; var coords=[]; var outputID='villageList'; var encodeID='cbBBEncode'; var isEncoded=true; function fnRefresh(){win.$('#'+outputID).html(coords.map(function(e){return isEncoded?'[coord]'+e+'[\/coord]':e;}).join(isEncoded?'\n':' '));} win.$(win.document).ready(function(){ if(win.$('#'+outputID).length<=0){ if(win.game_data.screen=='map'){ var srcHTML= '<div id="coord_picker">'+ '<span style="color:blue;text-decoration:underline;">dalesmckay\'s co-ordinate picker v7.1:</span><br/><br/>'+ '<input type="checkbox" id="cbBBEncode" onClick="isEncoded=this.checked;fnRefresh();"'+(isEncoded?'checked':'')+'/>BB-Codes<br/>'+ '<textarea id="'+outputID+'" cols="40" rows="10" value="" onFocus="this.select();"/>'+ '</div>'; ele=win.$('body').append(win.$(srcHTML)); win.TWMap.map._handleClick=function(e){ var pos=this.coordByEvent(e); var coord=pos.join("|"); var ii=coords.indexOf(coord); if(ii>=0){ coords.splice(ii,1); } else{ coords.push(coord); } fnRefresh(); return false; }; } else{ alert("Run this script from the Map.\nRedirecting now..."); self.location=win.game_data.link_base_pure.replace(/screen\=\w*/i,"screen=map"); } } }); void(0);

que pega as coordenadas _pelo clique_ (estando no mapa) e coloca em uma caixinha no _canto inferior da tela_ , ou adicionar os farms aos **favoritos** e depois, na praça de reunião, dentro do box **"destino"** , copiar todo o texto que tiver lá nos favoritos e jogar no box do fxutility, que o programa já identifica as coordenadas _sem precisar apagar nada_
