import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import pg8000.native 
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random
import string
from urllib.parse import urlparse, unquote

# Carrega as variáveis do arquivo .env (O Cofre)
load_dotenv()

# ==========================================
# CONFIGURAÇÃO DE CONEXÃO SEGURA E BLINDADA
# ==========================================
DB_URL = os.getenv("DATABASE_URL")

# Blindagem contra a ausência do arquivo .env no Desktop
if DB_URL:
    if isinstance(DB_URL, bytes):
        DB_URL = DB_URL.decode('utf-8')
    parsed_url = urlparse(DB_URL)
    DB_USER = unquote(parsed_url.username) if parsed_url.username else None
    DB_PASS = unquote(parsed_url.password) if parsed_url.password else None
    DB_HOST = parsed_url.hostname
    DB_PORT = parsed_url.port or 5432
    DB_NAME = parsed_url.path.lstrip("/") if parsed_url.path else ""
else:
    DB_USER = DB_PASS = DB_HOST = DB_PORT = DB_NAME = None

USUARIO_ID = None
USUARIO_ROLE = None
USUARIO_NOME = ""

# Adicione esta variável global fora da função
_conexao_global = None

def executar_db(query, params=(), fetchall=False, fetchone=False):
    """Executa comandos no PostgreSQL de forma segura reaproveitando a conexão."""
    global _conexao_global
    
    if not DB_HOST:
        return False, "⚠️ Arquivo .env ausente! Coloque-o na mesma pasta."

    try:
        # Só cria uma nova conexão se não existir uma aberta
        if _conexao_global is None:
            _conexao_global = pg8000.native.Connection(
                user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, database=DB_NAME
            )
        
        # Prepara e executa a query usando a conexão global
        if params:
            for i in range(len(params)):
                query = query.replace("%s", f":v{i}", 1)
            kwargs = {f"v{i}": val for i, val in enumerate(params)}
            res = _conexao_global.run(query, **kwargs)
        else:
            res = _conexao_global.run(query)
            
        resultado = None
        if fetchall:
            resultado = res
        elif fetchone:
            resultado = res[0] if res else None
            
        return True, resultado

    except Exception as e:
        print(f"Erro no Banco de Dados: {e}")
        # Se der erro (ex: a internet caiu ou o Supabase derrubou a conexão por inatividade)
        # Limpamos a variável. Na próxima tentativa, ele reconecta automaticamente.
        try:
            if _conexao_global:
                _conexao_global.close()
        except:
            pass
        _conexao_global = None 
        return False, str(e)
    
    # REMOVIDO o bloco 'finally' com conn.close() namoral.
    # A conexão ficará viva e reaproveitável!


# ==========================================
# AUTENTICAÇÃO E RECUPERAÇÃO DE SENHA
# ==========================================

def login_sistema(username, password):
    global USUARIO_ID, USUARIO_ROLE, USUARIO_NOME
    query = "SELECT id, nome, role FROM usuarios WHERE username = %s AND password = %s"
    sucesso, usuario = executar_db(query, (username, password), fetchone=True)
    
    if sucesso and usuario:
        USUARIO_ID = usuario[0]
        USUARIO_NOME = usuario[1]
        USUARIO_ROLE = usuario[2]
        registrar_log("Login efetuado com sucesso")
        return True, usuario
    
    mensagem_erro = usuario if not sucesso and "Arquivo .env" in str(usuario) else "Usuário ou senha inválidos."
    return False, mensagem_erro

def obter_email_usuario():
    sucesso, res = executar_db("SELECT email FROM usuarios WHERE id = %s", (USUARIO_ID,), fetchone=True)
    return res[0] if sucesso and res else ""

def atualizar_perfil(novo_email, nova_senha=None):
    if nova_senha:
        return executar_db("UPDATE usuarios SET email = %s, password = %s WHERE id = %s", (novo_email, nova_senha, USUARIO_ID))
    else:
        return executar_db("UPDATE usuarios SET email = %s WHERE id = %s", (novo_email, USUARIO_ID))

def enviar_email_recuperacao(destinatario, nome, nova_senha):
    remetente = os.getenv("EMAIL_USER")
    senha_app = os.getenv("EMAIL_PASS") 
    
    if not remetente or not senha_app:
        return False, "Erro de servidor: Configuração de e-mail ausente (.env)."
        
    try:
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = "Recuperação de Senha - Meu Gestor"
        
        corpo = f"Olá {nome},\n\nSua solicitação de redefinição de senha foi concluída com sucesso.\n\nSua nova senha temporária de acesso é: {nova_senha}\n\nRecomendamos fortemente que você altere esta senha no menu 'Meu Perfil > Ajustes' assim que acessar o sistema.\n\nAtenciosamente,\nEquipe Meu Gestor"
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha_app)
        server.send_message(msg)
        server.quit()
        return True, "E-mail enviado com sucesso."
    except Exception as e:
        return False, f"Falha ao enviar e-mail via SMTP: {e}"

def redefinir_senha_por_email(email):
    query = "SELECT id, nome FROM usuarios WHERE email = %s"
    sucesso, res = executar_db(query, (email,), fetchone=True)
    
    if not res:
        return False, "E-mail não encontrado no sistema."
    
    nova_senha = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    sucesso_db, msg_db = executar_db("UPDATE usuarios SET password = %s WHERE id = %s", (nova_senha, res[0]))
    
    if sucesso_db:
        sucesso_email, msg_email = enviar_email_recuperacao(email, res[1], nova_senha)
        if sucesso_email:
            registrar_log(f"Recuperação de senha solicitada para {email}")
            return True, "A nova senha foi enviada para o seu e-mail com sucesso!"
        else:
            return False, f"Senha redefinida no banco, mas erro ao enviar o e-mail: {msg_email}"
            
    return False, "Erro ao atualizar a senha no banco de dados."


# ==========================================
# GESTÃO DE CARTÕES DE CRÉDITO
# ==========================================

def _garantir_tabelas_cartao():
    executar_db('''
        CREATE TABLE IF NOT EXISTS cartoes (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            nome TEXT NOT NULL,
            limite REAL NOT NULL,
            dia_fechamento INTEGER NOT NULL,
            dia_vencimento INTEGER NOT NULL,
            cor TEXT
        )
    ''')
    executar_db('''
        CREATE TABLE IF NOT EXISTS compras_cartao (
            id SERIAL PRIMARY KEY,
            cartao_id INTEGER REFERENCES cartoes(id) ON DELETE CASCADE,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            data_compra DATE NOT NULL,
            parcela_atual INTEGER DEFAULT 1,
            total_parcelas INTEGER DEFAULT 1,
            mes_fatura INTEGER NOT NULL,
            ano_fatura INTEGER NOT NULL,
            categoria TEXT,
            status TEXT DEFAULT 'ABERTA' -- Pode ser ABERTA, FECHADA ou PAGA
        )
    ''')

def adicionar_cartao(nome, limite, dia_fechamento, dia_vencimento, cor):
    _garantir_tabelas_cartao()
    query = "INSERT INTO cartoes (usuario_id, nome, limite, dia_fechamento, dia_vencimento, cor) VALUES (%s, %s, %s, %s, %s, %s)"
    return executar_db(query, (USUARIO_ID, nome.upper(), float(limite), int(dia_fechamento), int(dia_vencimento), cor))

def listar_cartoes():
    _garantir_tabelas_cartao()
    query = "SELECT id, nome, limite, dia_fechamento, dia_vencimento, cor FROM cartoes WHERE usuario_id = %s ORDER BY nome"
    sucesso, res = executar_db(query, (USUARIO_ID,), fetchall=True)
    return res if sucesso and res else []

def atualizar_cartao(id_cartao, nome, limite, dia_fechamento, dia_vencimento, cor):
    _garantir_tabelas_cartao()
    query = "UPDATE cartoes SET nome=%s, limite=%s, dia_fechamento=%s, dia_vencimento=%s, cor=%s WHERE id=%s AND usuario_id=%s"
    return executar_db(query, (nome.upper(), float(limite), int(dia_fechamento), int(dia_vencimento), cor, id_cartao, USUARIO_ID))

def deletar_cartao(id_cartao):
    return executar_db("DELETE FROM cartoes WHERE id = %s AND usuario_id = %s", (id_cartao, USUARIO_ID))

def obter_limite_disponivel(cartao_id, limite_total):
    _garantir_tabelas_cartao()
    query = "SELECT SUM(valor) FROM compras_cartao WHERE cartao_id = %s AND status IN ('ABERTA', 'FECHADA')"
    s, r = executar_db(query, (cartao_id,), fetchone=True)
    consumido = r[0] if s and r and r[0] else 0.0
    return float(limite_total) - float(consumido)

def is_fatura_fechada(cartao_id, mes, ano):
    """Verifica se a fatura já foi fechada ou paga (trava de segurança)"""
    _garantir_tabelas_cartao()
    query = "SELECT COUNT(*) FROM compras_cartao WHERE cartao_id=%s AND mes_fatura=%s AND ano_fatura=%s AND status IN ('FECHADA', 'PAGA')"
    s, r = executar_db(query, (cartao_id, mes, ano), fetchone=True)
    return True if s and r and r[0] > 0 else False

def adicionar_compra_cartao(cartao_id, descricao, valor_total, data_compra, parcelas, categoria, mes_inicial, ano_inicial):
    _garantir_tabelas_cartao()
    
    # Bloqueio de segurança no backend
    if is_fatura_fechada(cartao_id, int(mes_inicial), int(ano_inicial)):
        return False, f"A fatura {mes_inicial:02d}/{ano_inicial} já está fechada."

    valor_parcela = float(valor_total) / int(parcelas)
    data_base_fatura = datetime(int(ano_inicial), int(mes_inicial), 1)

    try:
        for i in range(int(parcelas)):
            data_fatura_atual = data_base_fatura + relativedelta(months=i)
            mes_fat = data_fatura_atual.month
            ano_fat = data_fatura_atual.year
            
            desc_final = f"{descricao} ({i+1}/{parcelas})" if int(parcelas) > 1 else descricao
            
            query = '''
                INSERT INTO compras_cartao 
                (cartao_id, usuario_id, descricao, valor, data_compra, parcela_atual, total_parcelas, mes_fatura, ano_fatura, categoria, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ABERTA')
            '''
            executar_db(query, (cartao_id, USUARIO_ID, desc_final, valor_parcela, data_compra, i+1, int(parcelas), mes_fat, ano_fat, categoria))
        
        return True, "Compra registrada com sucesso!"
    except Exception as e:
        return False, f"Erro ao registrar compra: {e}"

def atualizar_compra_cartao(id_compra, desc, valor, data_compra, categoria, mes_fat, ano_fat):
    _garantir_tabelas_cartao()
    
    # Garante que não está movendo a compra para uma fatura já fechada
    sucesso_c, cartao = executar_db("SELECT cartao_id FROM compras_cartao WHERE id=%s", (id_compra,), fetchone=True)
    if sucesso_c and cartao and is_fatura_fechada(cartao[0], int(mes_fat), int(ano_fat)):
        return False, f"A fatura alvo ({int(mes_fat):02d}/{ano_fat}) já está fechada."

    query = '''UPDATE compras_cartao SET descricao=%s, valor=%s, data_compra=%s, 
               categoria=%s, mes_fatura=%s, ano_fatura=%s 
               WHERE id=%s AND usuario_id=%s AND status='ABERTA' '''
    return executar_db(query, (desc, float(valor), data_compra, categoria, int(mes_fat), int(ano_fat), id_compra, USUARIO_ID))

def listar_compras_fatura(cartao_id, mes, ano):
    _garantir_tabelas_cartao()
    query = '''
        SELECT id, descricao, valor, data_compra, categoria, status 
        FROM compras_cartao 
        WHERE cartao_id = %s AND usuario_id = %s AND mes_fatura = %s AND ano_fatura = %s
        ORDER BY data_compra ASC
    '''
    sucesso, res = executar_db(query, (cartao_id, USUARIO_ID, mes, ano), fetchall=True)
    return res if sucesso and res else []

def fechar_fatura_cartao(cartao_id, mes, ano):
    _garantir_tabelas_cartao()
    s_cartao, cartao = executar_db("SELECT nome, dia_vencimento FROM cartoes WHERE id = %s AND usuario_id = %s", (cartao_id, USUARIO_ID), fetchone=True)
    if not s_cartao or not cartao:
        return False, "Cartão não encontrado."
        
    nome_cartao = cartao[0]
    dia_vencimento = cartao[1]

    query_soma = "SELECT SUM(valor) FROM compras_cartao WHERE cartao_id = %s AND usuario_id = %s AND mes_fatura = %s AND ano_fatura = %s AND status = 'ABERTA'"
    s_soma, res_soma = executar_db(query_soma, (cartao_id, USUARIO_ID, mes, ano), fetchone=True)
    total_fatura = res_soma[0] if res_soma and res_soma[0] else 0.0

    if total_fatura <= 0:
        return False, "Não há compras em aberto para fechar."

    try:
        data_venc = datetime(ano, mes, dia_vencimento).strftime('%Y-%m-%d')
    except ValueError:
        data_venc = (datetime(ano, mes, 1) + relativedelta(day=31)).strftime('%Y-%m-%d')

    try:
        desc_fatura = f"Fatura {nome_cartao} - {mes:02d}/{ano}"
        executar_db("INSERT INTO categorias (usuario_id, nome, tipo) VALUES (%s, 'CARTÃO DE CRÉDITO', 'SAIDA') ON CONFLICT DO NOTHING", (USUARIO_ID,))
        adicionar_conta_pagar(desc_fatura, total_fatura, data_venc, "CARTÃO DE CRÉDITO", False, "MENSAL")
        executar_db("UPDATE compras_cartao SET status = 'FECHADA' WHERE cartao_id = %s AND mes_fatura = %s AND ano_fatura = %s AND status = 'ABERTA'", (cartao_id, mes, ano))
        
        return True, f"Fatura fechada! R$ {total_fatura:.2f} enviados para 'A Pagar'."
    except Exception as e:
        return False, f"Erro ao fechar fatura: {e}"

def reabrir_fatura_cartao(cartao_id, mes, ano):
    _garantir_tabelas_cartao()
    s_c, cartao = executar_db("SELECT nome FROM cartoes WHERE id=%s AND usuario_id=%s", (cartao_id, USUARIO_ID), fetchone=True)
    if not s_c or not cartao:
        return False, "Cartão não encontrado."
    
    desc_fatura = f"Fatura {cartao[0]} - {mes:02d}/{ano}"
    
    s_p, pend = executar_db("SELECT id FROM contas_a_pagar WHERE descricao=%s AND status='PENDENTE' AND usuario_id=%s", (desc_fatura, USUARIO_ID), fetchone=True)
    if not s_p or not pend:
        return False, "Fatura já foi paga em 'A Pagar' ou não foi encontrada. Não é possível reabrir."
    
    executar_db("DELETE FROM contas_a_pagar WHERE id=%s AND usuario_id=%s", (pend[0], USUARIO_ID))
    executar_db("UPDATE compras_cartao SET status='ABERTA' WHERE cartao_id=%s AND mes_fatura=%s AND ano_fatura=%s AND status='FECHADA'", (cartao_id, mes, ano))
    
    return True, "Fatura reaberta com sucesso e removida do 'A Pagar'."

def deletar_compra_cartao(id_compra):
    return executar_db("DELETE FROM compras_cartao WHERE id = %s AND usuario_id = %s AND status = 'ABERTA'", (id_compra, USUARIO_ID))


# ==========================================
# GESTÃO DE CATEGORIAS
# ==========================================

def listar_categorias_por_tipo(tipo):
    query = "SELECT nome FROM categorias WHERE usuario_id = %s AND tipo = %s ORDER BY nome"
    sucesso, res = executar_db(query, (USUARIO_ID, tipo), fetchall=True)
    return [r[0] for r in res] if sucesso else []

def adicionar_categoria(nome, tipo):
    query = "INSERT INTO categorias (usuario_id, nome, tipo) VALUES (%s, %s, %s)"
    return executar_db(query, (USUARIO_ID, nome.upper(), tipo))

def editar_categoria_inteligente(nome_antigo, nome_novo, tipo):
    try:
        s, r = executar_db("SELECT id FROM categorias WHERE nome = %s AND usuario_id = %s AND tipo = %s", (nome_novo.upper(), USUARIO_ID, tipo), fetchone=True)
        if s and r:
            return False, "Já existe uma categoria com este nome."

        executar_db("UPDATE categorias SET nome = %s WHERE nome = %s AND usuario_id = %s AND tipo = %s", 
                       (nome_novo.upper(), nome_antigo, USUARIO_ID, tipo))

        executar_db("UPDATE movimentacoes SET categoria = %s WHERE categoria = %s AND usuario_id = %s AND tipo_movimento = %s", 
                       (nome_novo.upper(), nome_antigo, USUARIO_ID, tipo))

        if tipo == 'SAIDA':
            executar_db("UPDATE contas_a_pagar SET categoria = %s WHERE categoria = %s AND usuario_id = %s", 
                           (nome_novo.upper(), nome_antigo, USUARIO_ID))
        elif tipo == 'ENTRADA':
            executar_db("UPDATE contas_a_receber SET categoria = %s WHERE categoria = %s AND usuario_id = %s", 
                           (nome_novo.upper(), nome_antigo, USUARIO_ID))

        return True, "Categoria renomeada com sucesso!"
    except Exception as e:
        return False, str(e)

def remover_categoria_segura(nome_cat, tipo):
    query_chk1 = "SELECT COUNT(*) FROM movimentacoes WHERE categoria = %s AND usuario_id = %s AND tipo_movimento = %s"
    s1, r1 = executar_db(query_chk1, (nome_cat, USUARIO_ID, tipo), fetchone=True)
    if s1 and r1[0] > 0:
        return False, f"Bloqueio: {r1[0]} lançamentos usam esta categoria."

    if tipo == 'SAIDA':
        query_chk2 = "SELECT COUNT(*) FROM contas_a_pagar WHERE categoria = %s AND usuario_id = %s"
        s2, r2 = executar_db(query_chk2, (nome_cat, USUARIO_ID), fetchone=True)
        if s2 and r2[0] > 0:
            return False, f"Bloqueio: {r2[0]} contas a pagar usam esta categoria."
    else:
        query_chk2 = "SELECT COUNT(*) FROM contas_a_receber WHERE categoria = %s AND usuario_id = %s"
        s2, r2 = executar_db(query_chk2, (nome_cat, USUARIO_ID), fetchone=True)
        if s2 and r2[0] > 0:
            return False, f"Bloqueio: {r2[0]} contas a receber usam esta categoria."

    return executar_db("DELETE FROM categorias WHERE nome = %s AND usuario_id = %s AND tipo = %s", (nome_cat, USUARIO_ID, tipo))


# ==========================================
# FLUXO DE CAIXA E BANCOS
# ==========================================

def listar_contas_bancarias():
    query = "SELECT nome FROM contas_bancarias WHERE usuario_id = %s ORDER BY nome"
    sucesso, res = executar_db(query, (USUARIO_ID,), fetchall=True)
    return [r[0] for r in res] if sucesso else []

def adicionar_movimentacao_avulsa(data, tipo, conta, desc, valor, cat):
    query = "INSERT INTO movimentacoes (usuario_id, data, tipo_movimento, conta_origem, descricao, valor, categoria) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    return executar_db(query, (USUARIO_ID, data, tipo, conta, desc, float(valor), cat))

def listar_movimentacoes_mes(ano, mes):
    query = "SELECT data, tipo_movimento, conta_origem, descricao, valor, categoria FROM movimentacoes WHERE usuario_id = %s AND EXTRACT(YEAR FROM data) = %s AND EXTRACT(MONTH FROM data) = %s ORDER BY data DESC"
    sucesso, res = executar_db(query, (USUARIO_ID, ano, mes), fetchall=True)
    if sucesso and res:
        return [[r[0], r[1], r[2], r[3], float(r[4]), r[5]] for r in res]
    return []

def listar_historico_filtrado(data_ini, data_fim):
    if USUARIO_ROLE == 'ADMIN':
        query = "SELECT id, data, tipo_movimento, conta_origem, descricao, valor, categoria FROM movimentacoes WHERE data >= %s AND data <= %s ORDER BY data DESC"
        params = (data_ini, data_fim)
    else:
        query = "SELECT id, data, tipo_movimento, conta_origem, descricao, valor, categoria FROM movimentacoes WHERE usuario_id = %s AND data >= %s AND data <= %s ORDER BY data DESC"
        params = (USUARIO_ID, data_ini, data_fim)
    
    sucesso, res = executar_db(query, params, fetchall=True)
    if sucesso and res:
         return [[r[0], r[1], r[2], r[3], r[4], float(r[5]), r[6]] for r in res]
    return []

def atualizar_movimentacao(id_mov, data, tipo, conta, desc, valor, cat):
    query = "UPDATE movimentacoes SET data=%s, tipo_movimento=%s, conta_origem=%s, descricao=%s, valor=%s, categoria=%s WHERE id=%s AND usuario_id=%s"
    return executar_db(query, (data, tipo, conta, desc, float(valor), cat, id_mov, USUARIO_ID))

def deletar_movimentacao(id_mov):
    return executar_db("DELETE FROM movimentacoes WHERE id = %s AND usuario_id = %s", (id_mov, USUARIO_ID))


# ==========================================
# CONTAS A PAGAR
# ==========================================

def adicionar_conta_pagar(descricao, valor, data_vencimento, categoria, recorrente=False, frequencia='MENSAL'):
    query = '''
        INSERT INTO contas_a_pagar (usuario_id, descricao, valor, data_vencimento, categoria, recorrente, frequencia, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDENTE')
    '''
    return executar_db(query, (USUARIO_ID, descricao, float(valor), data_vencimento, categoria, recorrente, frequencia))

def listar_contas_pendentes():
    query = "SELECT id, descricao, valor, data_vencimento, categoria, recorrente, frequencia FROM contas_a_pagar WHERE status = 'PENDENTE' AND usuario_id = %s ORDER BY data_vencimento ASC"
    sucesso, res = executar_db(query, (USUARIO_ID,), fetchall=True)
    if sucesso and res:
         return [[r[0], r[1], float(r[2]), r[3], r[4], r[5], r[6]] for r in res]
    return []

def processar_pagamento_conta(id_conta, conta_origem, data_pagamento_str, valor_pago=None):
    try:
        s, conta = executar_db("SELECT descricao, valor, data_vencimento, categoria, recorrente, frequencia FROM contas_a_pagar WHERE id = %s AND usuario_id = %s", (id_conta, USUARIO_ID), fetchone=True)
        if not s or not conta:
            return False, "Conta não encontrada."
            
        desc, valor_original, venc, cat, rec, freq = conta
        valor_pago = float(valor_pago) if valor_pago is not None else float(valor_original)

        executar_db('''
            INSERT INTO movimentacoes (usuario_id, data, tipo_movimento, conta_origem, descricao, valor, categoria)
            VALUES (%s, %s, 'SAIDA', %s, %s, %s, %s)
        ''', (USUARIO_ID, data_pagamento_str, conta_origem, f"Pagto: {desc}", valor_pago, cat))

        if valor_pago < float(valor_original):
            novo_saldo = float(valor_original) - valor_pago
            executar_db("UPDATE contas_a_pagar SET valor = %s WHERE id = %s", (novo_saldo, id_conta))
            msg = f"Pagamento parcial de R$ {valor_pago:.2f}. Resta R$ {novo_saldo:.2f}."
        else:
            executar_db("UPDATE contas_a_pagar SET status = 'PAGO', data_pagamento = %s WHERE id = %s", (data_pagamento_str, id_conta))
            msg = "Conta totalmente paga e baixada!"
            
            # --- MÁGICA DO CARTÃO DE CRÉDITO ---
            # Se for uma fatura, libera o limite das compras mudando o status para PAGA
            if desc.startswith("Fatura "):
                try:
                    parts = desc.split(" - ")
                    if len(parts) == 2:
                        cartao_nome = parts[0].replace("Fatura ", "")
                        mes_ano = parts[1].split("/")
                        s_c, cart = executar_db("SELECT id FROM cartoes WHERE nome=%s AND usuario_id=%s", (cartao_nome, USUARIO_ID), fetchone=True)
                        if s_c and cart:
                            executar_db("UPDATE compras_cartao SET status='PAGA' WHERE cartao_id=%s AND mes_fatura=%s AND ano_fatura=%s AND usuario_id=%s", (cart[0], int(mes_ano[0]), int(mes_ano[1]), USUARIO_ID))
                except:
                    pass
            # -----------------------------------

            if rec:
                novo_venc = venc
                if freq == 'MENSAL':
                    novo_venc += relativedelta(months=1)
                elif freq == 'ANUAL':
                    novo_venc += relativedelta(years=1)
                elif freq == 'SEMANAL':
                    novo_venc += relativedelta(weeks=1)
                    
                executar_db('''
                    INSERT INTO contas_a_pagar (usuario_id, descricao, valor, data_vencimento, categoria, recorrente, frequencia, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDENTE')
                ''', (USUARIO_ID, desc, float(valor_original), novo_venc, cat, rec, freq))

        return True, msg
    except Exception as e:
        return False, f"Erro ao processar: {e}"

def atualizar_conta_pagar(id_conta, descricao, valor, data_vencimento, categoria, recorrente, frequencia):
    query = '''
        UPDATE contas_a_pagar 
        SET descricao=%s, valor=%s, data_vencimento=%s, categoria=%s, recorrente=%s, frequencia=%s 
        WHERE id=%s AND usuario_id=%s
    '''
    return executar_db(query, (descricao, float(valor), data_vencimento, categoria, recorrente, frequencia, id_conta, USUARIO_ID))

def deletar_conta_pendente(id_conta):
    return executar_db("DELETE FROM contas_a_pagar WHERE id = %s AND usuario_id = %s AND status = 'PENDENTE'", (id_conta, USUARIO_ID))


# ==========================================
# CONTAS A RECEBER
# ==========================================

def _garantir_tabela_receber():
    executar_db('''
        CREATE TABLE IF NOT EXISTS contas_a_receber (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            data_vencimento DATE NOT NULL,
            categoria TEXT,
            recorrente BOOLEAN DEFAULT FALSE,
            frequencia TEXT DEFAULT 'MENSAL',
            status TEXT DEFAULT 'PENDENTE',
            data_pagamento DATE
        )
    ''')

def adicionar_conta_receber(descricao, valor, data_vencimento, categoria, recorrente=False, frequencia='MENSAL'):
    _garantir_tabela_receber()
    query = '''
        INSERT INTO contas_a_receber (usuario_id, descricao, valor, data_vencimento, categoria, recorrente, frequencia, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDENTE')
    '''
    return executar_db(query, (USUARIO_ID, descricao, float(valor), data_vencimento, categoria, recorrente, frequencia))

def listar_contas_receber_pendentes():
    _garantir_tabela_receber()
    query = "SELECT id, descricao, valor, data_vencimento, categoria, recorrente, frequencia FROM contas_a_receber WHERE status = 'PENDENTE' AND usuario_id = %s ORDER BY data_vencimento ASC"
    sucesso, res = executar_db(query, (USUARIO_ID,), fetchall=True)
    if sucesso and res:
         return [[r[0], r[1], float(r[2]), r[3], r[4], r[5], r[6]] for r in res]
    return []

def processar_recebimento_conta(id_conta, conta_destino, data_pagamento_str, valor_recebido=None):
    _garantir_tabela_receber()
    try:
        s, conta = executar_db("SELECT descricao, valor, data_vencimento, categoria, recorrente, frequencia FROM contas_a_receber WHERE id = %s AND usuario_id = %s", (id_conta, USUARIO_ID), fetchone=True)
        if not s or not conta:
            return False, "Conta não encontrada."
            
        desc, valor_original, venc, cat, rec, freq = conta
        valor_recebido = float(valor_recebido) if valor_recebido is not None else float(valor_original)

        executar_db('''
            INSERT INTO movimentacoes (usuario_id, data, tipo_movimento, conta_origem, descricao, valor, categoria)
            VALUES (%s, %s, 'ENTRADA', %s, %s, %s, %s)
        ''', (USUARIO_ID, data_pagamento_str, conta_destino, f"Recebimento: {desc}", valor_recebido, cat))

        if valor_recebido < float(valor_original):
            novo_saldo = float(valor_original) - valor_recebido
            executar_db("UPDATE contas_a_receber SET valor = %s WHERE id = %s", (novo_saldo, id_conta))
            msg = f"Recebimento parcial de R$ {valor_recebido:.2f}. Resta receber R$ {novo_saldo:.2f}."
        else:
            executar_db("UPDATE contas_a_receber SET status = 'PAGO', data_pagamento = %s WHERE id = %s", (data_pagamento_str, id_conta))
            msg = "Conta totalmente recebida e baixada com sucesso!"
            
            if rec:
                novo_venc = venc
                if freq == 'MENSAL':
                    novo_venc += relativedelta(months=1)
                elif freq == 'ANUAL':
                    novo_venc += relativedelta(years=1)
                elif freq == 'SEMANAL':
                    novo_venc += relativedelta(weeks=1)
                    
                executar_db('''
                    INSERT INTO contas_a_receber (usuario_id, descricao, valor, data_vencimento, categoria, recorrente, frequencia, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDENTE')
                ''', (USUARIO_ID, desc, float(valor_original), novo_venc, cat, rec, freq))

        return True, msg
    except Exception as e:
        return False, f"Erro ao processar recebimento: {e}"

def atualizar_conta_receber(id_conta, descricao, valor, data_vencimento, categoria, recorrente, frequencia):
    _garantir_tabela_receber()
    query = '''
        UPDATE contas_a_receber 
        SET descricao=%s, valor=%s, data_vencimento=%s, categoria=%s, recorrente=%s, frequencia=%s 
        WHERE id=%s AND usuario_id=%s
    '''
    return executar_db(query, (descricao, float(valor), data_vencimento, categoria, recorrente, frequencia, id_conta, USUARIO_ID))

def deletar_conta_receber_pendente(id_conta):
    _garantir_tabela_receber()
    return executar_db("DELETE FROM contas_a_receber WHERE id = %s AND usuario_id = %s AND status = 'PENDENTE'", (id_conta, USUARIO_ID))


# ==========================================
# PAINEL DE AUDITORIA E REGISTRO GERAL
# ==========================================

def registrar_novo_usuario(nome, email, username, password):
    try:
        s, r = executar_db("SELECT id FROM usuarios WHERE username = %s OR email = %s", (username, email), fetchone=True)
        if s and r:
            return False, "Nome de usuário ou E-mail já estão em uso."

        s2, res_id = executar_db('''
            INSERT INTO usuarios (nome, email, username, password, role)
            VALUES (%s, %s, %s, %s, 'USER')
            RETURNING id
        ''', (nome, email, username, password), fetchone=True)
        
        novo_id = res_id[0] if isinstance(res_id, (list, tuple)) else res_id

        executar_db("INSERT INTO contas_bancarias (usuario_id, nome) VALUES (%s, 'Carteira (Dinheiro)')", (novo_id,))
        categorias_iniciais = [('SALÁRIO', 'ENTRADA'), ('OUTRAS RECEITAS', 'ENTRADA'), ('ALIMENTAÇÃO', 'SAIDA'), ('MORADIA', 'SAIDA'), ('TRANSPORTE', 'SAIDA')]
        for cat, tipo in categorias_iniciais:
            executar_db("INSERT INTO categorias (usuario_id, nome, tipo) VALUES (%s, %s, %s)", (novo_id, cat, tipo))

        executar_db("INSERT INTO configuracoes (usuario_id, fullscreen) VALUES (%s, TRUE)", (novo_id,))
        registrar_log(f"Novo usuário registrado: {username}", force_id=novo_id)

        return True, "Conta criada com sucesso! Você já pode fazer o login."
    except Exception as e:
        return False, f"Erro ao criar conta: {e}"

def registrar_log(acao, force_id=None):
    id_log = force_id if force_id else USUARIO_ID
    if not id_log: return
    
    executar_db('''CREATE TABLE IF NOT EXISTS logs_acesso (
                    id SERIAL PRIMARY KEY,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario_id INTEGER,
                    acao TEXT
                  )''')
    executar_db("INSERT INTO logs_acesso (usuario_id, acao) VALUES (%s, %s)", (id_log, acao))

def listar_todos_usuarios():
    if USUARIO_ROLE != 'ADMIN':
        return []
        
    sucesso, res = executar_db("SELECT id, nome, email, username FROM usuarios ORDER BY id ASC", fetchall=True)
    return [[r[0], r[1], r[2], r[3]] for r in res] if sucesso and res else []

def listar_logs_acesso():
    if USUARIO_ROLE != 'ADMIN':
        return []
        
    executar_db('''CREATE TABLE IF NOT EXISTS logs_acesso (
                    id SERIAL PRIMARY KEY,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario_id INTEGER,
                    acao TEXT
                  )''')
    sucesso, res = executar_db("SELECT data_hora, usuario_id, acao FROM logs_acesso ORDER BY data_hora DESC LIMIT 50", fetchall=True)
    
    if sucesso and res:
         return [[r[0].strftime('%d/%m/%Y %H:%M:%S') if isinstance(r[0], datetime) else r[0], r[1], r[2]] for r in res]
    return []