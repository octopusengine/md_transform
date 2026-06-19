# Test parsování py_md_transform

Tento soubor ukazuje, co exportér umí parsovat. Každý blok má popis, potom Markdown code se zdrojovým zápisem a potom stejný zápis jako parsovaný obsah.

---

## Nadpisy

Podporované jsou nadpisy `#` až `######`.

```markdown
# Nadpis 1
## Nadpis 2
### Nadpis 3
```

# Nadpis 1
## Nadpis 2
### Nadpis 3

---

## Odstavce

Běžný neprázdný řádek se převádí na odstavec.

```markdown
Toto je běžný odstavec textu.
Další neprázdný řádek je další odstavec.
```

Toto je běžný odstavec textu.
Další neprázdný řádek je další odstavec.

---

## Kurzíva, tučné a tučná kurzíva

Podporované jsou základní hvězdičkové značky.

```markdown
*kurzíva*
**tučné**
***tučná kurzíva***
```

*kurzíva*
**tučné**
***tučná kurzíva***

---

## Zvýraznění

Zápis `==text==` se převádí na barevné zvýraznění pro světlý i tmavý režim.

```markdown
Toto je ==zvýrazněný text== v odstavci.
```

Toto je ==zvýrazněný text== v odstavci.

---

## Odkazy

Podporované jsou klasické Markdown odkazy, automatické URL a wiki odkazy.

```markdown
[OpenAI](https://openai.com)
https://example.com
[[test_basic]]
[[test_basic|vlastní popisek]]
[[neexistující_stránka]]
```

[OpenAI](https://openai.com)
https://example.com
[[test_basic]]
[[test_basic|vlastní popisek]]
[[neexistující_stránka]]

---

## Checkboxy

Řádky `- [ ]` a `- [x]` se převádí na nezaškrtnutý a zaškrtnutý checkbox.

```markdown
- [ ] nedokončený úkol
- [x] hotový úkol
```

- [ ] nedokončený úkol
- [x] hotový úkol

---

## Citace

Řádky začínající `>` se spojují do citace s odsazením a postranní linkou.

```markdown
> Toto je citace.
> Druhý řádek stejné citace.
```

> Toto je citace.
> Druhý řádek stejné citace.

---

## Vodorovná čára

Samostatný řádek `---` se převádí na `<hr>`. Řádek typu `---action` se nebere jako čára.

```markdown
---
---action
```

---
---action

---

## Tabulky

Tabulka se parsuje, pokud má hlavičku, oddělovací řádek a řádky začínající i končící znakem `|`.

```markdown
| Sloupec A | Sloupec B |
| --- | --- |
| *kurzíva* | **tučné** |
| ==mark== | [[test_basic]] |
```

| Sloupec A | Sloupec B |
| --- | --- |
| *kurzíva* | **tučné** |
| ==mark== | [[test_basic]] |

---

## Blokový kód

Trojité zpětné apostrofy se převádí na blok kódu. Obsah uvnitř se dál neparsuje.

````markdown
```python
print("Ahoj")
```
````

```python
print("Ahoj")
```

---

## Matematický blok

Blok mezi samostatnými řádky `$$` se vykresluje přes KaTeX.

```markdown
$$
E = mc^2
$$
```

$$
E = mc^2
$$

---

## Inline matematika

Inline matematika se nechává v textu a vykresluje ji KaTeX skript v prohlížeči.

```markdown
Pythagorova věta: $a^2 + b^2 = c^2$.
```

Pythagorova věta: $a^2 + b^2 = c^2$.

---

## QR code blok

Blok kódu s jazykem `qrcode` se převádí na QR kód.

````markdown
```qrcode
https://example.com
```
````

```qrcode
https://example.com
```

---

## HTML escapování

HTML značky ve vstupním Markdownu se vypíšou jako text, nevkládají se jako živé HTML.

```markdown
<strong>Toto zůstane text.</strong>
```

<strong>Toto zůstane text.</strong>

