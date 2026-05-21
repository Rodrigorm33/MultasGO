"""
Crawler da Tabela FIPE via Parallelum API v2.
Baixa marcas → modelos → anos → preços e salva no SQLite local.

Uso:
    python -m app.fipe.crawler              # Crawl completo (carros + motos + caminhões)
    python -m app.fipe.crawler --tipo cars   # Só carros
    python -m app.fipe.crawler --stats       # Ver estatísticas do banco
"""

import time
import sys
import urllib.request
import json
from typing import Optional

from app.fipe.database import FipeDB

BASE_URL = "https://fipe.parallelum.com.br/api/v2"
HEADERS = {"User-Agent": "MultasGO-FipeCrawler/1.0"}

# Tipos de veículo
TIPOS = {
    "cars": {"nome": "Carros", "tipo_int": 1},
    "motorcycles": {"nome": "Motos", "tipo_int": 2},
    "trucks": {"nome": "Caminhões", "tipo_int": 3},
}

# Rate limiting: API permite 1000/dia sem token
# 1.5s = ~40 req/min = seguro contra 429
DELAY_ENTRE_REQUESTS = 1.5  # segundos
DELAY_APOS_429 = 60  # esperar 1 min após rate limit


class FipeCrawler:
    def __init__(self, db: Optional[FipeDB] = None):
        self.db = db or FipeDB()
        self.requests_feitos = 0
        self.erros = 0

    def _get(self, url: str) -> Optional[dict | list]:
        """GET com retry, backoff e rate limiting."""
        for tentativa in range(5):
            try:
                time.sleep(DELAY_ENTRE_REQUESTS)
                req = urllib.request.Request(url, headers=HEADERS)
                resp = urllib.request.urlopen(req, timeout=15)
                self.requests_feitos += 1
                return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                self.erros += 1
                if e.code == 429:
                    wait = DELAY_APOS_429 * (tentativa + 1)
                    print(f"\n    429 Rate Limit! Aguardando {wait}s...")
                    time.sleep(wait)
                elif tentativa < 4:
                    time.sleep(3 * (tentativa + 1))
                else:
                    print(f"\n    FALHOU: {url} - HTTP {e.code}")
                    return None
            except Exception as e:
                self.erros += 1
                if tentativa < 4:
                    time.sleep(3 * (tentativa + 1))
                else:
                    print(f"\n    FALHOU: {url} - {e}")
                    return None

    def crawl_referencias(self):
        """Baixa tabelas de referência (meses disponíveis)."""
        print("Baixando referências FIPE...")
        refs = self._get(f"{BASE_URL}/references")
        if refs:
            self.db.salvar_referencias(refs)
            print(f"  {len(refs)} referências salvas (última: {refs[0]['month']})")
        return refs

    def crawl_tipo(self, tipo: str):
        """Crawl completo de um tipo de veículo (cars/motorcycles/trucks)."""
        info = TIPOS[tipo]
        print(f"\n{'='*60}")
        print(f"CRAWLING: {info['nome'].upper()}")
        print(f"{'='*60}")

        # 1. Buscar marcas
        marcas = self._get(f"{BASE_URL}/{tipo}/brands")
        if not marcas:
            print(f"  ERRO: Não conseguiu buscar marcas de {tipo}")
            return

        self.db.salvar_marcas(tipo, marcas)
        print(f"  {len(marcas)} marcas encontradas")

        total_veiculos_tipo = 0

        # Verificar marcas já completas (para continuar de onde parou)
        marcas_completas = set()
        with self.db._conn() as conn:
            rows = conn.execute(
                "SELECT marca FROM fipe_crawler_log WHERE tipo=? AND status='completo'", (tipo,)
            ).fetchall()
            marcas_completas = {r[0] for r in rows}

        if marcas_completas:
            print(f"  Pulando {len(marcas_completas)} marcas já baixadas")

        # 2. Para cada marca, buscar modelos
        for i, marca in enumerate(marcas, 1):
            marca_cod = marca["code"]
            marca_nome = marca["name"]

            if marca_nome in marcas_completas:
                continue

            log_id = self.db.log_inicio(tipo, marca_nome)
            print(f"\n  [{i}/{len(marcas)}] {marca_nome}...")

            modelos = self._get(f"{BASE_URL}/{tipo}/brands/{marca_cod}/models")
            if not modelos:
                self.db.log_fim(log_id, 0, 0, "Falha ao buscar modelos")
                continue

            self.db.salvar_modelos(tipo, marca_cod, modelos)
            total_veiculos_marca = 0

            # 3. Para cada modelo, buscar anos
            for j, modelo in enumerate(modelos, 1):
                modelo_cod = modelo["code"]
                modelo_nome = modelo["name"]

                anos = self._get(f"{BASE_URL}/{tipo}/brands/{marca_cod}/models/{modelo_cod}/years")
                if not anos:
                    continue

                # 4. Para cada ano, buscar preço
                batch = []
                for ano in anos:
                    ano_cod = ano["code"]
                    preco = self._get(
                        f"{BASE_URL}/{tipo}/brands/{marca_cod}/models/{modelo_cod}/years/{ano_cod}"
                    )
                    if preco:
                        batch.append(preco)

                if batch:
                    self.db.salvar_veiculos_batch(batch)
                    total_veiculos_marca += len(batch)

                # Progresso inline
                sys.stdout.write(f"\r    Modelos: {j}/{len(modelos)} | Veículos: {total_veiculos_marca} | Requests: {self.requests_feitos}")
                sys.stdout.flush()

            print(f"\n    OK: {len(modelos)} modelos, {total_veiculos_marca} veículos salvos")
            total_veiculos_tipo += total_veiculos_marca
            self.db.log_fim(log_id, len(modelos), total_veiculos_marca)

        print(f"\n  TOTAL {info['nome']}: {total_veiculos_tipo} veículos")
        return total_veiculos_tipo

    def crawl_completo(self, tipos: Optional[list[str]] = None):
        """Crawl completo de todos os tipos."""
        tipos = tipos or list(TIPOS.keys())
        inicio = time.time()

        print("=" * 60)
        print("FIPE CRAWLER - MultasGO")
        print(f"Banco: {self.db.db_path}")
        print(f"API: {BASE_URL}")
        print(f"Tipos: {', '.join(tipos)}")
        print("=" * 60)

        # Referências
        self.crawl_referencias()

        # Crawl cada tipo
        total_geral = 0
        for tipo in tipos:
            if tipo in TIPOS:
                total = self.crawl_tipo(tipo)
                if total:
                    total_geral += total

        duracao = time.time() - inicio
        minutos = duracao / 60

        print(f"\n{'='*60}")
        print("CRAWLER FINALIZADO")
        print(f"{'='*60}")
        print(f"  Total veículos: {total_geral}")
        print(f"  Requests feitos: {self.requests_feitos}")
        print(f"  Erros: {self.erros}")
        print(f"  Duração: {minutos:.1f} minutos")
        print(f"  Banco: {self.db.db_path}")

        # Estatísticas finais
        stats = self.db.estatisticas()
        print(f"\n  Banco de dados:")
        print(f"    Registros: {stats['total_registros']}")
        print(f"    Marcas: {stats['marcas']}")
        print(f"    Modelos: {stats['modelos_unicos']}")
        print(f"    Carros: {stats['carros']}")
        print(f"    Motos: {stats['motos']}")
        print(f"    Caminhões: {stats['caminhoes']}")
        print(f"    Referência: {stats['mes_referencia']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="FIPE Crawler - MultasGO")
    parser.add_argument("--tipo", choices=["cars", "motorcycles", "trucks"],
                        help="Tipo específico (default: todos)")
    parser.add_argument("--stats", action="store_true", help="Mostrar estatísticas do banco")
    parser.add_argument("--db", default=None, help="Caminho do banco SQLite")
    args = parser.parse_args()

    db = FipeDB(args.db) if args.db else FipeDB()

    if args.stats:
        stats = db.estatisticas()
        print("Estatísticas do banco FIPE:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        prog = db.progresso_crawler()
        print("\nProgresso do crawler:")
        for k, v in prog.items():
            print(f"  {k}: {v}")
        return

    crawler = FipeCrawler(db)
    tipos = [args.tipo] if args.tipo else None
    crawler.crawl_completo(tipos)


if __name__ == "__main__":
    main()
