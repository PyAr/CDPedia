<html><head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<title>CDPedia - PyAr</title>
</head><body><br>
<center>
<font color="#0000ff" size="+3">CD Pedia<br>
<br>

<font color="#ff0000" size="+2">
$mensaje
<br>

<br>
<font color="#000000" size="+2">Buscar en los títulos<br><br>

<table>
<tr>
 <td valign="top">Palabras completas</td>
 <td>
    <form method="get" action="/dosearch">
    <input name="keywords"></input>
    <input type="submit" value="Buscar">
    </form>
 </td>
</tr>
<tr>
 <td valign="top">Búsqueda detallada</td>
 <td>
    <form method="get" action="/detallada">
    <input name="keywords"></input>
    <input type="submit" value="Buscar">
    </form>
 </td>
</tr>
</table>

<br>
<font color="#000000" size="+2">Ver páginas<br><br>
<table>
<tr>
 <td>
    <form method="get" action="/listfull">
    <input type="submit" value="Listado completo"></input>
    </form>
 </td>
 <td>
    <form method="get" action="/al_azar">
    <input type="submit" value="Alguna al azar"></input>
    </form>
 </td>
</tr>
</table>

<br>
<font color="#000000" size="+1">Estadísticas<br></font>
<font size="-1">
<table>
<tr>
 <td>Páginas</td>
 <td>$stt_pag</td>
</tr>
<tr>
 <td>Imágenes</td>
 <td>$stt_img</td>
</tr>
</table>
</font>

<font size="-1">
<br>
- - - <br>
Otro desarrollo de PyAr - Python Argentina
</font>
</center>
</body></html>
