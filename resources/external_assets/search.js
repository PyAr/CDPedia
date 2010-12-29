
$(document).ready(function() {
    var search_string = "";
    var buscando = "buscando";
    var esperando = "generando índice"
    var index_ready = false;
    var get_resultados = function () {
        var status="NOTDONE";
        
        var res_completa="";
        var res_detallada="";
        
        $.get('/ajax/buscar/resultado', function(data) { 
                var html;
                status = data.status;
                res_completa = $.fn.base64Decode(data.res_completa);
                res_detallada = $.fn.base64Decode(data.res_detallada);
                if (status == "NOTDONE")
                {
                    setTimeout(get_resultados, 500);
                    buscando += ".";
                    html = "<h2>Resultados para: "+search_string+"</h2>"+"<i>"+buscando+"</i><br/>"+res_completa + res_detallada;
                }
                else{
                    buscando = "";
                    if (res_detallada === "" && res_completa === "")
                        {html = "<h2>No se encontró nada para lo ingresado!</h2>";}
                    else
                        {html = "<h2>Resultados para: "+search_string+"</h2><br/>"+res_completa + res_detallada;}
                }
                $("#content").html(html);
                
        });
    };
    
    var index_is_ready = function(on_ready){
        $.get('/ajax/index/ready', function(data) {
            if (data===true){
                index_ready = true;
                if (on_ready){
                    esperando = "generando índice";
                    on_ready();
                }
            }
            else{
                esperando += ".";
                $("#content").html('<h1><font color="#0000cc" size="+1">Por favor, aguarde mientras CDpedia termina de cargar el índice</font></h1><br/>'+"<i>"+esperando+"</i>");
                setTimeout(index_is_ready, 1000, buscar);
            }
        });
    };
    
    var buscar = function(){
        $.get('/ajax/buscar', {keywords:search_string});
        buscando = "buscando";
        setTimeout(get_resultados,500);
        $("#content").html("<h2>Resultados para: "+search_string+"</h2> <br/> <i>buscando</i><br/>");
    };
    

    $("#search-form").submit(function(event){
        event.preventDefault();
        search_string = $("#searchInput").val();
        if (search_string){
            index_is_ready(buscar);
        }
    });

});
