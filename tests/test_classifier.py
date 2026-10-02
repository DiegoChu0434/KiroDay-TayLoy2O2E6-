"""
Prueba de la logica de clasificacion contra el CSV real, sin dependencia de boto3.
Reimplementa el import de forma que boto3 sea opcional.

Uso:
    python tests/test_classifier.py
"""
import sys
import types

# Stub de boto3 para poder importar el modulo analyzer sin la dependencia real.
if "boto3" not in sys.modules:
    stub = types.ModuleType("boto3")
    stub.client = lambda *a, **k: None
    sys.modules["boto3"] = stub

sys.path.insert(0, "src/analyzer")
import analyzer  # noqa: E402

CSV_PATH = "data/ha00_20260930.csv"


def main():
    with open(CSV_PATH, encoding="latin-1") as f:
        body = f.read()

    registros = analyzer.parse_csv(body)
    summary = analyzer.build_summary(
        registros,
        "tailoy-poc-s3-bucket-raw",
        "tai-loy/maestro/raw/ASPRD.ha00/ha00_20260930.csv",
    )

    print(f"Total errores:       {summary['lote']['total_errores']}")
    print(f"Clientes afectados:  {summary['lote']['clientes_afectados']}")
    print("\nPor categoria:")
    for c in summary["categorias"]:
        print(f"  {c['conteo']:>5}  {c['severidad']:<8} {c['categoria']}  ({c['equipo']})")
    print(f"\nAlerta diferenciada STOCK/ATP: {summary['alerta_stock']['conteo']}")
    print(f"Top cliente: {summary['top_clientes'][0] if summary['top_clientes'] else 'n/a'}")

    print("\nRunbook y responsable por categoria:")
    for c in summary["categorias"]:
        sol = c.get("solucion", {})
        resp = c.get("responsable", {})
        print(
            f"  {c['categoria']:<32} -> {resp.get('actor', '-')}/{resp.get('frente', '-')} "
            f"<{resp.get('correo', '-')}> ({len(sol.get('pasos', []))} pasos)"
        )

    # asserts basicos
    assert summary["lote"]["total_errores"] == 2474, "El total deberia ser 2474"
    cats = {c["categoria"]: c["conteo"] for c in summary["categorias"]}
    assert cats.get("PARTNER_FUNCTIONS_FALTANTES", 0) == 1480
    assert cats.get("DATOS_CLIENTE_INCOMPLETOS", 0) == 404
    assert summary["alerta_stock"]["conteo"] == 337

    # cada categoria debe traer su runbook de solucion
    for c in summary["categorias"]:
        assert "solucion" in c, f"Falta runbook en {c['categoria']}"
        assert c["solucion"]["area_responsable"], f"Sin responsable en {c['categoria']}"
        assert c["solucion"]["pasos"], f"Sin pasos en {c['categoria']}"
    # los 4 runbooks del analista con su responsable esperado
    por_cat = {c["categoria"]: c["solucion"]["area_responsable"] for c in summary["categorias"]}
    assert por_cat.get("PARTNER_FUNCTIONS_FALTANTES") == "Datos Maestros"
    assert por_cat.get("STOCK_INSUFICIENTE_ATP") == "Operaciones / Logística tienda"

    # cada categoria debe traer su responsable (actor/frente/correo)
    resp_por_cat = {c["categoria"]: c.get("responsable", {}) for c in summary["categorias"]}
    assert resp_por_cat["PARTNER_FUNCTIONS_FALTANTES"]["correo"] == "datos_maestros@tailoy.com.pe"
    assert resp_por_cat["DATOS_CLIENTE_INCOMPLETOS"]["correo"] == "jsalvatierra@tailoy.com.pe"
    assert resp_por_cat["STOCK_INSUFICIENTE_ATP"]["actor"] == "PRODUCTO"
    assert resp_por_cat["CUENTA_MAYOR_INEXISTENTE"]["correo"] == "bpantoja@tailoy.com.pe"
    # ningun correo debe tener el typo 'tailohy'
    for c in summary["categorias"]:
        assert "tailohy" not in c.get("responsable", {}).get("correo", ""), "typo tailohy detectado"
    print("\nOK: todas las aserciones pasaron.")


if __name__ == "__main__":
    main()
