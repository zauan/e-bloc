## Obtine ID asociatie, ID apartament.

Te loghezi pe pagina, rulezi inspectare, te duci la Network, filtrezi dupa INDEX si faci click dreapta, apoi Copy -> Copy all listed as cURL

<img width="1709" alt="image" src="https://github.com/user-attachments/assets/96ec05b8-a4f4-4997-8f29-94e599e9b05b" />


Te duci apoi pe https://curlconverter.com/, si dai paste. Sus, gasesti cookies. Exemplu:

```yaml
cookies = {
    'username': 'email@exemplu.com',
    'asoc-cur': 'XXXXX',
    'avizier-luna-cur': '-',
    'facturi-luna-cur': '-',
    'index-luna-cur': '-',
    **'home-ap-cur': 'XXXXX_XX',**
    'home-stat-cur': '6',
    'PHPSESSID': '4kh25v0ua12r973i10ug06sspo',
}
```
    'asoc-cur': 'XXXXX', = asociatie
    **'home-ap-cur': 'XXXXX_XX',** = asociatie _ ID apartament
 
