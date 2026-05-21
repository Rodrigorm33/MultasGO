"""
Banco SQLite local para dados da Tabela FIPE.
Armazena marcas, modelos e preços para consulta offline.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fipe.db")


class FipeDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._criar_tabelas()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _criar_tabelas(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS fipe_referencias (
                    codigo TEXT PRIMARY KEY,
                    mes TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS fipe_marcas (
                    tipo TEXT NOT NULL,
                    codigo TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    PRIMARY KEY (tipo, codigo)
                );

                CREATE TABLE IF NOT EXISTS fipe_modelos (
                    tipo TEXT NOT NULL,
                    marca_codigo TEXT NOT NULL,
                    codigo TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    PRIMARY KEY (tipo, marca_codigo, codigo)
                );

                CREATE TABLE IF NOT EXISTS fipe_veiculos (
                    codigo_fipe TEXT NOT NULL,
                    ano_modelo INTEGER NOT NULL,
                    combustivel TEXT,
                    combustivel_sigla TEXT,
                    marca TEXT,
                    modelo TEXT,
                    preco TEXT,
                    preco_valor REAL,
                    mes_referencia TEXT,
                    tipo_veiculo INTEGER,
                    atualizado_em TEXT,
                    PRIMARY KEY (codigo_fipe, ano_modelo, combustivel_sigla)
                );

                CREATE TABLE IF NOT EXISTS fipe_crawler_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT,
                    marca TEXT,
                    total_modelos INTEGER DEFAULT 0,
                    total_veiculos INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pendente',
                    erro TEXT,
                    inicio TEXT,
                    fim TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_fipe_marca ON fipe_veiculos(marca);
                CREATE INDEX IF NOT EXISTS idx_fipe_modelo ON fipe_veiculos(modelo);
                CREATE INDEX IF NOT EXISTS idx_fipe_tipo ON fipe_veiculos(tipo_veiculo);
                CREATE INDEX IF NOT EXISTS idx_fipe_preco ON fipe_veiculos(preco_valor);
            """)

    # === Inserções ===

    def salvar_referencias(self, referencias: list[dict]):
        with self._conn() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO fipe_referencias (codigo, mes) VALUES (?, ?)",
                [(r["code"], r["month"]) for r in referencias]
            )

    def salvar_marcas(self, tipo: str, marcas: list[dict]):
        with self._conn() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO fipe_marcas (tipo, codigo, nome) VALUES (?, ?, ?)",
                [(tipo, m["code"], m["name"]) for m in marcas]
            )

    def salvar_modelos(self, tipo: str, marca_codigo: str, modelos: list[dict]):
        with self._conn() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO fipe_modelos (tipo, marca_codigo, codigo, nome) VALUES (?, ?, ?, ?)",
                [(tipo, marca_codigo, m["code"], m["name"]) for m in modelos]
            )

    def salvar_veiculo(self, dados: dict):
        preco_str = dados.get("price", "")
        preco_valor = self._parse_preco(preco_str)

        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO fipe_veiculos
                (codigo_fipe, ano_modelo, combustivel, combustivel_sigla, marca, modelo,
                 preco, preco_valor, mes_referencia, tipo_veiculo, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados.get("codeFipe", ""),
                dados.get("modelYear", 0),
                dados.get("fuel", ""),
                dados.get("fuelAcronym", ""),
                dados.get("brand", ""),
                dados.get("model", ""),
                preco_str,
                preco_valor,
                dados.get("referenceMonth", ""),
                dados.get("vehicleType", 0),
                datetime.now().isoformat()
            ))

    def salvar_veiculos_batch(self, lista: list[dict]):
        agora = datetime.now().isoformat()
        rows = []
        for d in lista:
            preco_valor = self._parse_preco(d.get("price", ""))
            rows.append((
                d.get("codeFipe", ""),
                d.get("modelYear", 0),
                d.get("fuel", ""),
                d.get("fuelAcronym", ""),
                d.get("brand", ""),
                d.get("model", ""),
                d.get("price", ""),
                preco_valor,
                d.get("referenceMonth", ""),
                d.get("vehicleType", 0),
                agora
            ))

        with self._conn() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO fipe_veiculos
                (codigo_fipe, ano_modelo, combustivel, combustivel_sigla, marca, modelo,
                 preco, preco_valor, mes_referencia, tipo_veiculo, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

    # === Consultas ===

    def buscar_por_codigo(self, codigo_fipe: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM fipe_veiculos WHERE codigo_fipe = ? ORDER BY ano_modelo DESC",
                (codigo_fipe,)
            ).fetchall()
            return [dict(r) for r in rows]

    def buscar_por_modelo(self, termo: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM fipe_veiculos WHERE modelo LIKE ? ORDER BY marca, modelo, ano_modelo DESC",
                (f"%{termo}%",)
            ).fetchall()
            return [dict(r) for r in rows]

    def buscar_por_marca(self, marca: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM fipe_veiculos WHERE marca LIKE ? ORDER BY modelo, ano_modelo DESC",
                (f"%{marca}%",)
            ).fetchall()
            return [dict(r) for r in rows]

    def listar_marcas(self, tipo: Optional[str] = None) -> list[dict]:
        with self._conn() as conn:
            if tipo:
                rows = conn.execute(
                    "SELECT DISTINCT marca, tipo_veiculo FROM fipe_veiculos WHERE tipo_veiculo = ? ORDER BY marca",
                    (self._tipo_para_int(tipo),)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT DISTINCT marca, tipo_veiculo FROM fipe_veiculos ORDER BY marca"
                ).fetchall()
            return [dict(r) for r in rows]

    def listar_modelos_por_marca(self, tipo: str, marca: str) -> list[dict]:
        tipo_int = self._tipo_para_int(tipo)
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT modelo
                FROM fipe_veiculos
                WHERE tipo_veiculo = ?
                  AND UPPER(TRIM(marca)) = UPPER(TRIM(?))
                ORDER BY modelo
                """,
                (tipo_int, marca)
            ).fetchall()
            return [{"modelo": r["modelo"]} for r in rows if r["modelo"]]

    def listar_anos_por_modelo(self, tipo: str, marca: str, modelo: str) -> list[dict]:
        tipo_int = self._tipo_para_int(tipo)
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT ano_modelo
                FROM fipe_veiculos
                WHERE tipo_veiculo = ?
                  AND UPPER(TRIM(marca)) = UPPER(TRIM(?))
                  AND UPPER(TRIM(modelo)) = UPPER(TRIM(?))
                ORDER BY ano_modelo DESC
                """,
                (tipo_int, marca, modelo)
            ).fetchall()
            return [{"ano": int(r["ano_modelo"])} for r in rows if r["ano_modelo"] is not None]

    def buscar_preco(self, tipo: str, marca: str, modelo: str, ano: int) -> Optional[dict]:
        tipo_int = self._tipo_para_int(tipo)
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    codigo_fipe,
                    ano_modelo,
                    combustivel,
                    combustivel_sigla,
                    marca,
                    modelo,
                    preco,
                    preco_valor,
                    mes_referencia,
                    tipo_veiculo
                FROM fipe_veiculos
                WHERE tipo_veiculo = ?
                  AND UPPER(TRIM(marca)) = UPPER(TRIM(?))
                  AND UPPER(TRIM(modelo)) = UPPER(TRIM(?))
                  AND ano_modelo = ?
                ORDER BY preco_valor DESC, combustivel_sigla
                LIMIT 1
                """,
                (tipo_int, marca, modelo, int(ano))
            ).fetchone()
            return dict(row) if row else None

    def estatisticas(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM fipe_veiculos").fetchone()[0]
            marcas = conn.execute("SELECT COUNT(DISTINCT marca) FROM fipe_veiculos").fetchone()[0]
            modelos = conn.execute("SELECT COUNT(DISTINCT modelo) FROM fipe_veiculos").fetchone()[0]
            carros = conn.execute("SELECT COUNT(*) FROM fipe_veiculos WHERE tipo_veiculo = 1").fetchone()[0]
            motos = conn.execute("SELECT COUNT(*) FROM fipe_veiculos WHERE tipo_veiculo = 2").fetchone()[0]
            caminhoes = conn.execute("SELECT COUNT(*) FROM fipe_veiculos WHERE tipo_veiculo = 3").fetchone()[0]
            ref = conn.execute("SELECT mes_referencia FROM fipe_veiculos LIMIT 1").fetchone()
            ultimo_update = conn.execute("SELECT MAX(atualizado_em) FROM fipe_veiculos").fetchone()[0]

            return {
                "total_registros": total,
                "marcas": marcas,
                "modelos_unicos": modelos,
                "carros": carros,
                "motos": motos,
                "caminhoes": caminhoes,
                "mes_referencia": ref[0] if ref else None,
                "ultima_atualizacao": ultimo_update
            }

    # === Log do Crawler ===

    def log_inicio(self, tipo: str, marca: str) -> int:
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO fipe_crawler_log (tipo, marca, status, inicio) VALUES (?, ?, 'rodando', ?)",
                (tipo, marca, datetime.now().isoformat())
            )
            return cursor.lastrowid

    def log_fim(self, log_id: int, total_modelos: int, total_veiculos: int, erro: str = None):
        status = "erro" if erro else "completo"
        with self._conn() as conn:
            conn.execute(
                "UPDATE fipe_crawler_log SET total_modelos=?, total_veiculos=?, status=?, erro=?, fim=? WHERE id=?",
                (total_modelos, total_veiculos, status, erro, datetime.now().isoformat(), log_id)
            )

    def progresso_crawler(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM fipe_crawler_log").fetchone()[0]
            completos = conn.execute("SELECT COUNT(*) FROM fipe_crawler_log WHERE status='completo'").fetchone()[0]
            erros = conn.execute("SELECT COUNT(*) FROM fipe_crawler_log WHERE status='erro'").fetchone()[0]
            rodando = conn.execute("SELECT COUNT(*) FROM fipe_crawler_log WHERE status='rodando'").fetchone()[0]
            return {
                "total_marcas": total,
                "completos": completos,
                "erros": erros,
                "rodando": rodando,
                "pendentes": total - completos - erros - rodando
            }

    # === Helpers ===

    @staticmethod
    def _parse_preco(preco_str: str) -> float:
        if not preco_str:
            return 0.0
        try:
            limpo = preco_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
            return float(limpo)
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def _tipo_para_int(tipo: str) -> int:
        return {"cars": 1, "carros": 1, "motorcycles": 2, "motos": 2, "trucks": 3, "caminhoes": 3}.get(tipo.lower(), 1)
