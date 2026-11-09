from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
import sqlite3
from datetime import date, datetime
import calendar

app = Flask(__name__)
app.secret_key = "chave-do-sistema"

def conectar():
    conexao = sqlite3.connect("banco.db")
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao

def normalizar_inscricao(numero):
    return "".join(caractere for caractere in numero if caractere.isdigit())

def criar_banco():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo_inscricao TEXT NOT NULL DEFAULT 'CNPJ',
            numero_inscricao TEXT NOT NULL,
            endereco TEXT,
            cidade TEXT,
            anotacoes TEXT,
            possui_assessoria INTEGER NOT NULL DEFAULT 0,
            periodicidade_assessoria INTEGER,
            data_inicio_assessoria TEXT,
            data_documento TEXT
        )
    """)

    # Verifica as colunas existentes na tabela empresas
    cursor.execute("PRAGMA table_info(empresas)")
    colunas = cursor.fetchall()

    nomes_colunas = []

    for coluna in colunas:
        nomes_colunas.append(coluna[1])

    # Migrações da tabela empresas
    if "possui_assessoria" not in nomes_colunas:
        cursor.execute("""
            ALTER TABLE empresas
            ADD COLUMN possui_assessoria INTEGER NOT NULL DEFAULT 0
        """)

    if "periodicidade_assessoria" not in nomes_colunas:
        cursor.execute("""
            ALTER TABLE empresas
            ADD COLUMN periodicidade_assessoria INTEGER
        """)

    if "data_inicio_assessoria" not in nomes_colunas:
        cursor.execute("""
            ALTER TABLE empresas
            ADD COLUMN data_inicio_assessoria TEXT
        """)

    if "data_documento" not in nomes_colunas:
        cursor.execute("""
            ALTER TABLE empresas
            ADD COLUMN data_documento TEXT
        """)

    # Criação independente da tabela de visitas realizadas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visitas_realizadas (
            empresa_id INTEGER NOT NULL,
            data_visita TEXT NOT NULL,
            data_realizacao TEXT NOT NULL,

            PRIMARY KEY (empresa_id, data_visita),

            FOREIGN KEY (empresa_id)
            REFERENCES empresas(id)
            ON DELETE CASCADE
        )
    """)

    conexao.commit()
    conexao.close()

def buscar_empresas():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            tipo_inscricao,
            numero_inscricao,
            endereco,
            cidade,
            anotacoes,
            possui_assessoria,
            periodicidade_assessoria,
            data_inicio_assessoria,
            data_documento
        FROM empresas
        ORDER BY nome
    """)

    empresas = cursor.fetchall()
    conexao.close()

    return empresas

def adicionar_meses(data_base, quantidade_meses):
    mes = data_base.month - 1 + quantidade_meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia)
    return date(ano, mes, dia)

def calcular_datas_documento(data_documento):
    if not data_documento:
        return None, None
    data_vencimento = adicionar_meses(data_documento, 12)
    data_antecipacao = adicionar_meses(data_vencimento, -2)
    return data_vencimento, data_antecipacao

def preparar_datas_documentos(empresas):
    datas_documentos = {}
    for empresa in empresas:
        empresa_id = empresa[0]
        data_documento = empresa[10]
        if not data_documento:
            datas_documentos[empresa_id] = {"documento": None, "vencimento": None, "antecipacao": None}
            continue
        try:
            data_documento = datetime.strptime(
                data_documento,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            datas_documentos[empresa_id] = {"documento": None, "vencimento": None, "antecipacao": None}
            continue
        data_vencimento, data_antecipacao = calcular_datas_documento(data_documento)
        datas_documentos[empresa_id] = {"documento": data_documento, "vencimento": data_vencimento, "antecipacao": data_antecipacao}
    return datas_documentos

def gerar_visitas_do_mes(empresas, ano, mes):
    visitas = []

    # Valida o ano e o mês solicitados
    try:
        date(ano, mes, 1)
    except (TypeError, ValueError):
        return visitas

    for empresa in empresas:
        empresa_id = empresa[0]
        nome = empresa[1]
        possui_assessoria = empresa[7]
        periodicidade = empresa[8]
        data_inicio = empresa[9]

        # Verifica se a empresa possui assessoria ativa
        if possui_assessoria != 1:
            continue

        # Verifica se existe uma data de início
        if not data_inicio:
            continue

        # Verifica se a periodicidade é válida
        if periodicidade not in PERIODICIDADES:
            continue

        # Converte a data armazenada no banco para um objeto date
        try:
            data_base = datetime.strptime(
                data_inicio,
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            continue

        # Calcula quantos meses existem entre a data inicial
        # e o mês que está sendo consultado
        diferenca_meses = (
            (ano - data_base.year) * 12
            + (mes - data_base.month)
        )

        # Calcula quantos meses devem ser adicionados
        # para encontrar a ocorrência correspondente
        if diferenca_meses < periodicidade:
            meses_decorridos = periodicidade
        else:
            meses_decorridos = (
                (diferenca_meses + periodicidade - 1)
                // periodicidade
            ) * periodicidade

        # Calcula a visita sempre a partir da data original
        data_visita = adicionar_meses(
            data_base,
            meses_decorridos
        )

        # Verifica se a ocorrência pertence ao mês consultado
        if (
            data_visita.year == ano
            and data_visita.month == mes
        ):
            visitas.append({
                "id": empresa_id,
                "nome": nome,
                "data": data_visita
            })

    # Organiza as visitas por data e nome da empresa
    return sorted(
        visitas,
        key=lambda visita: (
            visita["data"],
            visita["nome"].casefold()
        )
    )

def calcular_proxima_visita(data_inicio, periodicidade):
    if not data_inicio:
        return None
    if periodicidade not in PERIODICIDADES:
        return None
    try:
        data_base = datetime.strptime(data_inicio, "%Y-%m-%d").date()
    except ValueError:
        return None
    return adicionar_meses(data_base, periodicidade)

def preparar_proximas_visitas(empresas):
    proximas_visitas = {}

    for empresa in empresas:
        empresa_id = empresa[0]
        possui_assessoria = empresa[7]
        periodicidade = empresa[8]
        data_inicio = empresa[9]

        if possui_assessoria == 1:
            proximas_visitas[empresa_id] = calcular_proxima_visita(
                data_inicio,
                periodicidade
            )
        else:
            proximas_visitas[empresa_id] = None

    return proximas_visitas

def gerar_documentos_do_mes(empresas, ano, mes):
    documentos = []

    for empresa in empresas:
        empresa_id = empresa[0]
        nome = empresa[1]
        tipo_inscricao = empresa[2]
        numero_inscricao = empresa[3]
        data_original = empresa[10]

        if not data_original:
            continue

        try:
            data_original = datetime.strptime(
                data_original, "%Y-%m-%d"
            ).date()
        except ValueError:
            continue

        # Primeiro vencimento: 12 meses após a data original.
        vencimento = adicionar_meses(data_original, 12)

        # Primeira preparação: 2 meses antes do vencimento.
        data_preparacao = adicionar_meses(vencimento, -2)

        # Avança anualmente até alcançar o período consultado.
        while (
            (data_preparacao.year, data_preparacao.month)
            < (ano, mes)
        ):
            vencimento = adicionar_meses(vencimento, 12)
            data_preparacao = adicionar_meses(vencimento, -2)

        # Só inclui a empresa se a preparação ocorrer
        # exatamente no mês e ano consultados.
        if (
            data_preparacao.year == ano
            and data_preparacao.month == mes
        ):
            documentos.append({
                "id": empresa_id,
                "nome": nome,
                "tipo_inscricao": tipo_inscricao,
                "numero_inscricao": numero_inscricao,
                "data_documento": data_original,
                "data_preparacao": data_preparacao,
                "vencimento": vencimento
            })

    return sorted(
        documentos,
        key=lambda item: (
            item["data_preparacao"],
            item["nome"]
        )
    )

PERIODICIDADES = {1: "Mensal", 2: "Bimestral", 3: "Trimestral", 4: "Quadrimestral", 6: "Semestral"}

@app.route("/")
def inicio():
    empresas = buscar_empresas()
    proximas_visitas = preparar_proximas_visitas(empresas)
    datas_documentos = preparar_datas_documentos(empresas)
    return render_template("inicio.html", empresas=empresas, proximas_visitas=proximas_visitas, datas_documentos=datas_documentos)

@app.route("/empresas")
def empresas():
    lista_empresas = buscar_empresas()
    proximas_visitas = preparar_proximas_visitas(lista_empresas)
    datas_documentos = preparar_datas_documentos(lista_empresas)
    return render_template("empresas.html", empresas=lista_empresas, proximas_visitas=proximas_visitas, datas_documentos=datas_documentos)

@app.route("/cadastrar", methods=["GET", "POST"])
def cadastrar():
    if request.method == "GET":
        return render_template("cadastrar.html")
    
    nome = request.form["nome"]
    tipo_inscricao = request.form["tipo_inscricao"]
    numero_inscricao = request.form["numero_inscricao"]
    endereco = request.form["endereco"]
    cidade = request.form["cidade"]
    anotacoes = request.form["anotacoes"]
    data_documento = request.form.get("data_documento")
    if data_documento:
        try:
            datetime.strptime(data_documento, "%Y-%m-%d")
        except ValueError:
            flash("Data do documento inválida.", "erro")
            return redirect("/cadastrar")
    else:
        data_documento = None
    possui_assessoria = request.form.get("possui_assessoria", "0")
    periodicidade_assessoria = request.form.get("periodicidade_assessoria")
    data_inicio_assessoria = request.form.get("data_inicio_assessoria")
    if possui_assessoria == "1":
        if not periodicidade_assessoria:
            flash("Informe a periodicidade da assessoria.", "erro")
            return redirect("/cadastrar")
        try:
            periodicidade_assessoria = int(periodicidade_assessoria)
        except ValueError:
            flash("Periodicidade inválida.", "erro")
            return redirect("/cadastrar")
        if periodicidade_assessoria not in PERIODICIDADES:
            flash("Periodicidade inválida.", "erro")
            return redirect("/cadastrar")

        if not data_inicio_assessoria:
            flash("Informe a data de início da assessoria.", "erro")
            return redirect("/cadastrar")
        try:
            datetime.strptime(data_inicio_assessoria, "%Y-%m-%d")
        except ValueError:
            flash("Data de início inválida.", "erro")
            return redirect("/cadastrar")

    else:
        possui_assessoria = "0"
        periodicidade_assessoria = None
        data_inicio_assessoria = None

    conexao = conectar()
    cursor = conexao.cursor()

    # Verifica se a inscrição já está cadastrada
    cursor.execute("""
        SELECT id
        FROM empresas
        WHERE tipo_inscricao = ?
        AND numero_inscricao = ?
    """, (tipo_inscricao, numero_inscricao))

    empresa_existente = cursor.fetchone()

    if empresa_existente:
        conexao.close()
        flash("Já existe uma empresa cadastrada com esse número de inscrição.", "erro")
        return redirect("/cadastrar")

    # Realiza o cadastro
    cursor.execute("""
        INSERT INTO empresas (
            nome,
            tipo_inscricao,
            numero_inscricao,
            endereco,
            cidade,
            anotacoes,
            possui_assessoria,
            periodicidade_assessoria,
            data_inicio_assessoria,
            data_documento
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nome,
        tipo_inscricao,
        numero_inscricao,
        endereco,
        cidade,
        anotacoes,
        possui_assessoria,
        periodicidade_assessoria,
        data_inicio_assessoria,
        data_documento
    ))

    conexao.commit()
    conexao.close()

    flash("Empresa cadastrada com sucesso!", "sucesso")

    return redirect("/")

@app.route("/calendario")
def calendario():
    # 1. Define o mês e o ano consultados.
    hoje = date.today()

    mes = request.args.get("mes", default=hoje.month, type=int)
    ano = request.args.get("ano", default=hoje.year, type=int)

    # 2. Valida o mês.
    if mes < 1 or mes > 12:
        mes = hoje.month

    # 3. Define o nome dos meses.
    nomes_meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro"
    }

    # 4. Busca as empresas cadastradas.
    empresas = buscar_empresas()

    # 5. Gera as visitas previstas para o mês consultado.
    visitas = gerar_visitas_do_mes(empresas, ano, mes)

    # 6. Calcula o intervalo de datas do mês.
    inicio_mes = date(ano, mes, 1)

    if mes == 12:
        inicio_proximo_mes = date(ano + 1, 1, 1)
    else:
        inicio_proximo_mes = date(ano, mes + 1, 1)

    # 7. Consulta no banco as visitas já realizadas.
    conexao = conectar()

    try:
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT empresa_id, data_visita
            FROM visitas_realizadas
            WHERE data_visita >= ?
            AND data_visita < ?
        """, (
            inicio_mes.isoformat(),
            inicio_proximo_mes.isoformat()
        ))

        registros_realizados = cursor.fetchall()

    finally:
        conexao.close()

    # 8. Transforma os registros em um conjunto de identificadores.
    visitas_concluidas = {
        (empresa_id, data_visita)
        for empresa_id, data_visita in registros_realizados
    }

    # 9. Identifica quais visitas previstas já foram realizadas.
    for visita in visitas:
        chave = (
            visita["id"],
            visita["data"].isoformat()
        )

        visita["realizada"] = chave in visitas_concluidas

    # 10. Envia os dados para o template HTML.
    return render_template(
        "calendario.html",
        visitas=visitas,
        mes=mes,
        ano=ano,
        nome_mes=nomes_meses[mes]
    )

@app.route("/deletar/<int:id>", methods=["POST"])
def deletar(id):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT id FROM empresas WHERE id = ?",
        (id,)
    )

    empresa = cursor.fetchone()

    if empresa is None:
        conexao.close()
        flash("Empresa não encontrada.", "erro")
        return redirect("/empresas")

    cursor.execute(
        "DELETE FROM empresas WHERE id = ?",
        (id,)
    )

    conexao.commit()
    conexao.close()

    flash("Empresa excluída com sucesso!", "sucesso")

    return redirect("/empresas")

@app.route("/alterar/<int:empresa_id>", methods=["GET", "POST"])
def alterar(empresa_id):

    conexao = conectar()
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()

    try:
        # 1. Busca a empresa que será alterada.
        cursor.execute("""
            SELECT *
            FROM empresas
            WHERE id = ?
        """, (empresa_id,))

        empresa = cursor.fetchone()

        if empresa is None:
            flash("Empresa não encontrada.", "erro")
            return redirect(url_for("inicio"))

        # 2. Se for GET, apenas apresenta o formulário.
        if request.method == "GET":
            return render_template(
                "alterar.html",
                empresa=empresa
            )

        # 3. Recebe e trata os dados do formulário.
        nome = request.form.get("nome", "").strip()

        tipo_inscricao = request.form.get(
            "tipo_inscricao", ""
        ).strip().upper()

        numero_inscricao = normalizar_inscricao(
            request.form.get("numero_inscricao", "")
        )

        endereco = request.form.get("endereco", "").strip()
        cidade = request.form.get("cidade", "").strip()
        anotacoes = request.form.get("anotacoes", "").strip()

        data_documento = request.form.get(
            "data_documento", ""
        ).strip() or None

        possui_assessoria = (
            1 if request.form.get("possui_assessoria") == "1"
            else 0
        )

        periodicidade_assessoria = None
        data_inicio_assessoria = None

        # 4. Valida os campos obrigatórios.
        if not nome or not tipo_inscricao or not numero_inscricao:
            flash(
                "Preencha o nome, o tipo e o número da inscrição.",
                "erro"
            )
            return redirect(
                url_for("alterar", empresa_id=empresa_id)
            )

        # 5. Valida o tipo de inscrição.
        if tipo_inscricao not in ("CNPJ", "CAEPF"):
            flash("Tipo de inscrição inválido.", "erro")
            return redirect(
                url_for("alterar", empresa_id=empresa_id)
            )

        # 6. Verifica se outra empresa possui a mesma inscrição.
        cursor.execute("""
            SELECT id
            FROM empresas
            WHERE tipo_inscricao = ?
            AND numero_inscricao = ?
            AND id != ?
        """, (
            tipo_inscricao,
            numero_inscricao,
            empresa_id
        ))

        empresa_existente = cursor.fetchone()

        if empresa_existente:
            flash(
                "Já existe outra empresa cadastrada com esse número de inscrição.",
                "erro"
            )
            return redirect(
                url_for("alterar", empresa_id=empresa_id)
            )

        # 7. Valida a data do documento.
        if data_documento:
            try:
                datetime.strptime(data_documento, "%Y-%m-%d")
            except ValueError:
                flash("Data do documento inválida.", "erro")
                return redirect(
                    url_for("alterar", empresa_id=empresa_id)
                )

        # 8. Trata os dados da assessoria.
        if possui_assessoria == 1:

            periodicidade = request.form.get(
                "periodicidade_assessoria", ""
            ).strip()

            data_inicio = request.form.get(
                "data_inicio_assessoria", ""
            ).strip()

            if not periodicidade or not data_inicio:
                flash(
                    "Informe a periodicidade e a data de início da assessoria.",
                    "erro"
                )
                return redirect(
                    url_for("alterar", empresa_id=empresa_id)
                )

            # Converte a periodicidade para número inteiro.
            try:
                periodicidade_assessoria = int(periodicidade)
            except ValueError:
                flash("Periodicidade inválida.", "erro")
                return redirect(
                    url_for("alterar", empresa_id=empresa_id)
                )

            # Verifica se a periodicidade é permitida.
            if periodicidade_assessoria not in PERIODICIDADES:
                flash("Periodicidade inválida.", "erro")
                return redirect(
                    url_for("alterar", empresa_id=empresa_id)
                )

            # Valida a data de início da assessoria.
            try:
                datetime.strptime(data_inicio, "%Y-%m-%d")
            except ValueError:
                flash("Data de início da assessoria inválida.", "erro")
                return redirect(
                    url_for("alterar", empresa_id=empresa_id)
                )

            data_inicio_assessoria = data_inicio

        # 9. Atualiza os dados da empresa.
        cursor.execute("""
            UPDATE empresas
            SET
                nome = ?,
                tipo_inscricao = ?,
                numero_inscricao = ?,
                endereco = ?,
                cidade = ?,
                anotacoes = ?,
                possui_assessoria = ?,
                periodicidade_assessoria = ?,
                data_inicio_assessoria = ?,
                data_documento = ?
            WHERE id = ?
        """, (
            nome,
            tipo_inscricao,
            numero_inscricao,
            endereco,
            cidade,
            anotacoes,
            possui_assessoria,
            periodicidade_assessoria,
            data_inicio_assessoria,
            data_documento,
            empresa_id
        ))

        # 10. Confirma a alteração no banco.
        conexao.commit()

        flash("Cadastro atualizado com sucesso.", "sucesso")

        return redirect(url_for("inicio"))

    finally:
        # 11. Fecha a conexão em qualquer situação.
        conexao.close()

@app.route("/documentos")
def documentos():
    hoje = date.today()

    mes = request.args.get("mes", default=hoje.month, type=int)
    ano = request.args.get("ano", default=hoje.year, type=int)

    if mes < 1 or mes > 12:
        mes = hoje.month

    empresas = buscar_empresas()
    documentos_mes = gerar_documentos_do_mes(empresas, ano, mes)

    nomes_meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março",
        4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro",
        10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    return render_template(
        "documentos.html",
        documentos=documentos_mes,
        mes=mes,
        ano=ano,
        nome_mes=nomes_meses[mes]
    )

@app.route("/relatorios/empresas")
def relatorio_empresas():
    empresas = buscar_empresas()
    datas_documentos = preparar_datas_documentos(empresas)
    return render_template("relatorio_empresas.html", empresas=empresas, datas_documentos=datas_documentos, data_emissao=date.today().strftime("%d/%m/%Y"))

@app.route("/visitas/alternar", methods=["POST"])
def alternar_visita():

    dados = request.get_json(silent=True) or {}

    empresa_id = dados.get("empresa_id")
    data_visita = dados.get("data_visita")
    realizada = dados.get("realizada")

    # Valida os dados recebidos.
    try:
        empresa_id = int(empresa_id)

        data_visita = datetime.strptime(
            data_visita,
            "%Y-%m-%d"
        ).date()

    except (ValueError, TypeError):
        return jsonify({
            "sucesso": False,
            "mensagem": "Dados inválidos."
        }), 400

    if not isinstance(realizada, bool):
        return jsonify({
            "sucesso": False,
            "mensagem": "Situação inválida."
        }), 400

    conexao = conectar()
    cursor = conexao.cursor()

    # Verifica se a empresa existe.
    cursor.execute(
        "SELECT id FROM empresas WHERE id = ?",
        (empresa_id,)
    )

    empresa = cursor.fetchone()

    if empresa is None:
        conexao.close()

        return jsonify({
            "sucesso": False,
            "mensagem": "Empresa não encontrada."
        }), 404

    if realizada:

        # Registra a visita como realizada.
        cursor.execute("""
            INSERT INTO visitas_realizadas (
                empresa_id,
                data_visita,
                data_realizacao
            )
            VALUES (?, ?, ?)
            ON CONFLICT (empresa_id, data_visita)
            DO UPDATE SET
                data_realizacao = excluded.data_realizacao
        """, (
            empresa_id,
            data_visita.isoformat(),
            datetime.now().isoformat(timespec="seconds")
        ))

    else:

        # Remove o registro para voltar a visita ao estado pendente.
        cursor.execute("""
            DELETE FROM visitas_realizadas
            WHERE empresa_id = ?
            AND data_visita = ?
        """, (
            empresa_id,
            data_visita.isoformat()
        ))

    conexao.commit()
    conexao.close()

    return jsonify({
        "sucesso": True,
        "realizada": realizada
    })

if __name__ == "__main__":
    criar_banco()
    app.run(debug=True)