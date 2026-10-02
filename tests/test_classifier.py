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

    # asserts basicos
    assert summary["lote"]["total_errores"] == 2474, "El total deberia ser 2474"
    cats = {c["categoria"]: c["conteo"] for c in summary["categorias"]}
    assert cats.get("PARTNER_FUNCTIONS_FALTANTES", 0) == 1480
    assert cats.get("DATOS_CLIENTE_INCOMPLETOS", 0) == 404
    assert summary["alerta_stock"]["conteo"] == 337
    print("\nOK: todas las aserciones pasaron.")


if __name__ == "__main__":
    main()
