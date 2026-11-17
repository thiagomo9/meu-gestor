import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
from datetime import datetime
import os
import banco

# ==========================================
# VERIFICAÇÃO DE BIBLIOTECAS (PDF E EXCEL)
# ==========================================
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import green, red, black, HexColor
    PDF_DISPONIVEL = True
except ImportError:
    PDF_DISPONIVEL = False

try:
    import pandas as pd
    EXCEL_DISPONIVEL = True
except ImportError:
    EXCEL_DISPONIVEL = False

class TelaHistorico(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.dados_atuais = [] 
        self.mapa_cartoes = {} # Guarda os IDs dos cartões para o filtro
        
        self.total_in = 0.0
        self.total_out = 0.0
        self.total_boletos = 0.0
        self.total_receber = 0.0
        self.total_cartao = 0.0

        lbl_titulo = ctk.CTkLabel(self, text="Histórico Geral e Relatórios", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(pady=(20, 10))

        # ==========================================
        # FRAME DE FILTROS E AÇÕES
        # ==========================================
        self.frame_filtros = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_filtros.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(self.frame_filtros, text="Origem/Filtro:").pack(side="left", padx=(0, 5))
        self.combo_origem = ctk.CTkComboBox(self.frame_filtros, values=["Visão Geral"], width=170)
        self.combo_origem.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.frame_filtros, text="Data Início:").pack(side="left", padx=(0, 5))
        self.entry_data_ini = ctk.CTkEntry(self.frame_filtros, width=95)
        primeiro_dia_mes = datetime.today().replace(day=1)
        self.entry_data_ini.insert(0, primeiro_dia_mes.strftime('%d/%m/%Y'))
        self.entry_data_ini.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.frame_filtros, text="Data Fim:").pack(side="left", padx=(0, 5))
        self.entry_data_fim = ctk.CTkEntry(self.frame_filtros, width=95)
        self.entry_data_fim.insert(0, datetime.today().strftime('%d/%m/%Y'))
        self.entry_data_fim.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.frame_filtros, text="Categoria:").pack(side="left", padx=(0, 5))
        self.combo_categoria = ctk.CTkComboBox(self.frame_filtros, values=["Todas"], width=130)
        self.combo_categoria.pack(side="left", padx=(0, 15))

        self.btn_filtrar = ctk.CTkButton(self.frame_filtros, text="Buscar", width=80, command=self.buscar_historico)
        self.btn_filtrar.pack(side="left", padx=(0, 20))

        # --- BOTÕES DE EXPORTAÇÃO ---
        self.btn_pdf = ctk.CTkButton(self.frame_filtros, text="Gerar PDF", fg_color="#C0392B", hover_color="#922B21", width=100, command=self.gerar_pdf)
        self.btn_pdf.pack(side="right")
        
        self.btn_excel = ctk.CTkButton(self.frame_filtros, text="Gerar Excel", fg_color="#27AE60", hover_color="#1E8449", width=100, command=self.gerar_excel)
        self.btn_excel.pack(side="right", padx=(0, 10))

        # ==========================================
        # FRAME DE TOTAIS
        # ==========================================
        self.frame_totais = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_totais.pack(fill="x", padx=20, pady=5)
        
        self.lbl_resumo_in = ctk.CTkLabel(self.frame_totais, text="Entradas: R$ 0.00", text_color="#2ECC71", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_resumo_in.pack(side="left", padx=(0, 20))
        
        self.lbl_resumo_out = ctk.CTkLabel(self.frame_totais, text="Saídas: R$ 0.00", text_color="#E74C3C", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_resumo_out.pack(side="left", padx=(0, 20))

        self.lbl_resumo_apagar = ctk.CTkLabel(self.frame_totais, text="A Pagar: R$ 0.00", text_color="#F39C12", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_resumo_apagar.pack(side="left", padx=(0, 20))
        
        self.lbl_resumo_areceber = ctk.CTkLabel(self.frame_totais, text="A Receber: R$ 0.00", text_color="#1ABC9C", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_resumo_areceber.pack(side="left")

        # ==========================================
        # LISTA DE RESULTADOS
        # ==========================================
        self.frame_lista = ctk.CTkFrame(self, corner_radius=10)
        self.frame_lista.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        cabecalho = ctk.CTkFrame(self.frame_lista, fg_color="transparent")
        cabecalho.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(cabecalho, text="Data", width=80, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(cabecalho, text="Tipo / Status", width=120, anchor="center", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(cabecalho, text="Descrição", width=200, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5)
        ctk.CTkLabel(cabecalho, text="Categoria", width=130, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5)
        ctk.CTkLabel(cabecalho, text="Valor", width=100, anchor="e", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=5)
        ctk.CTkLabel(cabecalho, text="Ação", width=80, anchor="center", font=ctk.CTkFont(weight="bold")).grid(row=0, column=5, padx=20)

        self.scroll_historico = ctk.CTkScrollableFrame(self.frame_lista)
        self.scroll_historico.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Inicia buscando os dados
        self.atualizar_filtros()
        self.buscar_historico()

    # ==========================================
    # LÓGICA E BANCO DE DADOS
    # ==========================================

    def atualizar_filtros(self):
        """Puxa as categorias e os cartões mais recentes do banco para popular os filtros"""
        # Filtro de Categorias
        cats_in = banco.listar_categorias_por_tipo('ENTRADA') or []
        cats_out = banco.listar_categorias_por_tipo('SAIDA') or []
        todas_cats = ["Todas"] + sorted(list(set(cats_in + cats_out)))
        self.combo_categoria.configure(values=todas_cats)

        # Filtro de Origem (Fluxos + Cartões)
        cartoes = banco.listar_cartoes()
        self.mapa_cartoes = {f"Cartão: {c[1]}": c[0] for c in cartoes}
        opcoes_origem = [
            "Visão Geral", 
            "Apenas Entradas", 
            "Apenas Saídas", 
            "Contas a Pagar", 
            "Contas a Receber", 
            "Todos os Cartões"
        ] + list(self.mapa_cartoes.keys())
        
        # Mantém a seleção atual se ela ainda existir, caso contrário volta para Visão Geral
        origem_atual = self.combo_origem.get()
        self.combo_origem.configure(values=opcoes_origem)
        if origem_atual not in opcoes_origem:
            self.combo_origem.set("Visão Geral")

    def buscar_historico(self):
        self.atualizar_filtros() 
        
        origem_selecionada = self.combo_origem.get()
        str_ini = self.entry_data_ini.get().strip()
        str_fim = self.entry_data_fim.get().strip()
        cat_selecionada = self.combo_categoria.get()

        try:
            data_ini_dt = datetime.strptime(str_ini, '%d/%m/%Y').date()
            data_fim_dt = datetime.strptime(str_fim, '%d/%m/%Y').date()
            
            data_ini_str = data_ini_dt.strftime('%Y-%m-%d')
            data_fim_str = data_fim_dt.strftime('%Y-%m-%d')
            
            self.dados_atuais = []
            self.total_boletos = 0.0
            self.total_receber = 0.0
            
            # SELEÇÃO: FLUXOS BÁSICOS DE CAIXA
            if origem_selecionada in ["Visão Geral", "Apenas Entradas", "Apenas Saídas"]:
                resultados_brutos = banco.listar_historico_filtrado(data_ini_str, data_fim_str)
                
                for r in resultados_brutos:
                    # R = [id, data, tipo, conta, desc, valor, cat]
                    if origem_selecionada == "Apenas Entradas" and r[2] != "ENTRADA":
                        continue
                    if origem_selecionada == "Apenas Saídas" and r[2] != "SAIDA":
                        continue
                    if cat_selecionada != "Todas" and r[6] != cat_selecionada:
                        continue
                    
                    self.dados_atuais.append(r)
                    
                # A Pagar e A Receber aparecem apenas se for "Visão Geral"
                if origem_selecionada == "Visão Geral":
                    todas_pendentes = banco.listar_contas_pendentes()
                    for p in todas_pendentes:
                        id_c, desc_c, valor_c, venc_c, cat_c, rec_c, freq_c = p
                        if isinstance(venc_c, str): 
                            venc_c = datetime.strptime(venc_c, '%Y-%m-%d').date()
                        if data_ini_dt <= venc_c <= data_fim_dt:
                            if cat_selecionada == "Todas" or cat_c == cat_selecionada:
                                self.total_boletos += float(valor_c)
                                # Adiciona à lista principal para aparecer na tela, PDF e Excel
                                self.dados_atuais.append((id_c, venc_c, "A PAGAR", "-", desc_c, float(valor_c), cat_c))
                                
                    todas_receber = banco.listar_contas_receber_pendentes()
                    for p in todas_receber:
                        id_c, desc_c, valor_c, venc_c, cat_c, rec_c, freq_c = p
                        if isinstance(venc_c, str): 
                            venc_c = datetime.strptime(venc_c, '%Y-%m-%d').date()
                        if data_ini_dt <= venc_c <= data_fim_dt:
                            if cat_selecionada == "Todas" or cat_c == cat_selecionada:
                                self.total_receber += float(valor_c)
                                # Adiciona à lista principal para aparecer na tela, PDF e Excel
                                self.dados_atuais.append((id_c, venc_c, "A RECEBER", "-", desc_c, float(valor_c), cat_c))

            # SELEÇÃO: APENAS CONTAS A PAGAR
            elif origem_selecionada == "Contas a Pagar":
                todas_pendentes = banco.listar_contas_pendentes()
                for p in todas_pendentes:
                    id_c, desc_c, valor_c, venc_c, cat_c, rec_c, freq_c = p
                    if isinstance(venc_c, str): 
                        venc_c = datetime.strptime(venc_c, '%Y-%m-%d').date()
                    if data_ini_dt <= venc_c <= data_fim_dt:
                        if cat_selecionada == "Todas" or cat_c == cat_selecionada:
                            # Formatação Padrão: (id, data, tipo, conta, desc, valor, cat)
                            self.dados_atuais.append((id_c, venc_c, "A PAGAR", "-", desc_c, float(valor_c), cat_c))
                            
            # SELEÇÃO: APENAS CONTAS A RECEBER
            elif origem_selecionada == "Contas a Receber":
                todas_receber = banco.listar_contas_receber_pendentes()
                for p in todas_receber:
                    id_c, desc_c, valor_c, venc_c, cat_c, rec_c, freq_c = p
                    if isinstance(venc_c, str): 
                        venc_c = datetime.strptime(venc_c, '%Y-%m-%d').date()
                    if data_ini_dt <= venc_c <= data_fim_dt:
                        if cat_selecionada == "Todas" or cat_c == cat_selecionada:
                            # Formatação Padrão: (id, data, tipo, conta, desc, valor, cat)
                            self.dados_atuais.append((id_c, venc_c, "A RECEBER", "-", desc_c, float(valor_c), cat_c))

            # SELEÇÃO: TODOS OS CARTÕES (Consolida tudo)
            elif origem_selecionada == "Todos os Cartões":
                query = '''
                    SELECT cc.id, cc.data_compra, cc.status, cc.descricao, cc.valor, cc.categoria, c.nome 
                    FROM compras_cartao cc
                    JOIN cartoes c ON cc.cartao_id = c.id
                    WHERE cc.usuario_id = %s AND cc.data_compra >= %s AND cc.data_compra <= %s 
                    ORDER BY cc.data_compra DESC
                '''
                s, res = banco.executar_db(query, (banco.USUARIO_ID, data_ini_str, data_fim_str), fetchall=True)
                
                if s and res:
                    for r in res:
                        if cat_selecionada == "Todas" or r[5] == cat_selecionada:
                            status_formatado = f"CARTÃO ({r[2]})"
                            nome_conta_fantasma = f"Cartão: {r[6]}"
                            self.dados_atuais.append((r[0], r[1], status_formatado, nome_conta_fantasma, r[3], r[4], r[5]))
                            
            # SELEÇÃO: CARTÃO DE CRÉDITO ESPECÍFICO
            else:
                id_cartao = self.mapa_cartoes.get(origem_selecionada)
                if id_cartao:
                    query = '''
                        SELECT id, data_compra, status, descricao, valor, categoria 
                        FROM compras_cartao 
                        WHERE cartao_id = %s AND usuario_id = %s AND data_compra >= %s AND data_compra <= %s 
                        ORDER BY data_compra DESC
                    '''
                    s, res = banco.executar_db(query, (id_cartao, banco.USUARIO_ID, data_ini_str, data_fim_str), fetchall=True)
                    
                    if s and res:
                        for r in res:
                            if cat_selecionada == "Todas" or r[5] == cat_selecionada:
                                status_formatado = f"CARTÃO ({r[2]})"
                                nome_conta_fantasma = origem_selecionada.replace("Cartão: ", "")
                                self.dados_atuais.append((r[0], r[1], status_formatado, nome_conta_fantasma, r[3], r[4], r[5]))
            
            self.exibir_resultados(self.dados_atuais, origem_selecionada)
            
        except ValueError:
            messagebox.showerror("Erro de Formato", "As datas devem estar no formato DD/MM/AAAA.")

    def exibir_resultados(self, resultados, origem):
        for widget in self.scroll_historico.winfo_children():
            widget.destroy()

        self.total_in = 0.0
        self.total_out = 0.0
        self.total_cartao = 0.0
        self.total_receber = 0.0
        self.total_boletos = 0.0

        if not resultados:
            ctk.CTkLabel(self.scroll_historico, text="Nenhum registro encontrado neste período/categoria.", text_color="gray").pack(pady=40)
            self.lbl_resumo_in.configure(text="")
            self.lbl_resumo_out.configure(text="")
            self.lbl_resumo_apagar.configure(text="")
            self.lbl_resumo_areceber.configure(text="")
            return

        # Ordena visualmente por data
        resultados.sort(key=lambda x: x[1])

        for mov in resultados:
            id_mov, data_mov, tipo, conta, desc, valor, cat = mov
            
            linha = ctk.CTkFrame(self.scroll_historico, fg_color="gray15")
            linha.pack(fill="x", pady=2)
            
            data_br = data_mov.strftime('%d/%m/%Y')
            
            if tipo == "ENTRADA":
                self.total_in += valor
                cor_tipo = "#2ECC71"
            elif tipo == "SAIDA":
                self.total_out += valor
                cor_tipo = "#E74C3C"
            elif tipo == "A PAGAR":
                self.total_boletos += valor
                cor_tipo = "#F39C12" # Laranja
            elif tipo == "A RECEBER":
                self.total_receber += valor
                cor_tipo = "#1ABC9C" # Verde Água (Teal)
            else:
                self.total_cartao += valor
                cor_tipo = "#8A2BE2" # Roxo

            ctk.CTkLabel(linha, text=data_br, width=80, anchor="w").grid(row=0, column=0, padx=5, pady=5)
            ctk.CTkLabel(linha, text=tipo, width=120, anchor="center", text_color=cor_tipo).grid(row=0, column=1, padx=5, pady=5)
            ctk.CTkLabel(linha, text=desc, width=200, anchor="w").grid(row=0, column=2, padx=5, pady=5)
            ctk.CTkLabel(linha, text=cat, width=130, anchor="w").grid(row=0, column=3, padx=5, pady=5)
            ctk.CTkLabel(linha, text=f"R$ {valor:.2f}", width=100, anchor="e", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=5, pady=5)
            
            # Bloqueia edições complexas de previsões ou cartões direto no histórico
            if tipo in ["ENTRADA", "SAIDA"]:
                btn_editar = ctk.CTkButton(
                    linha, text="Editar", width=60, fg_color="gray30", hover_color="gray40",
                    command=lambda dados=mov: self.abrir_popup_edicao(dados)
                )
                btn_editar.grid(row=0, column=5, padx=20, pady=5)
            elif tipo == "A PAGAR":
                ctk.CTkLabel(linha, text="Via Gestão", text_color="gray").grid(row=0, column=5, padx=20, pady=5)
            elif tipo == "A RECEBER":
                ctk.CTkLabel(linha, text="Via Gestão", text_color="gray").grid(row=0, column=5, padx=20, pady=5)
            else:
                # Compras de cartão
                rotulo = f"Via {conta}" if origem == "Todos os Cartões" else "Via Fatura"
                ctk.CTkLabel(linha, text=rotulo, text_color="gray").grid(row=0, column=5, padx=20, pady=5)

        # Atualiza o rodapé dinamicamente com base no Filtro de Origem
        if origem == "Visão Geral":
            self.lbl_resumo_in.configure(text=f"Entradas: R$ {self.total_in:.2f}", text_color="#2ECC71")
            self.lbl_resumo_out.configure(text=f"Saídas: R$ {self.total_out:.2f}", text_color="#E74C3C")
            self.lbl_resumo_apagar.configure(text=f"A Pagar: R$ {self.total_boletos:.2f}")
            self.lbl_resumo_areceber.configure(text=f"A Receber: R$ {self.total_receber:.2f}", text_color="#1ABC9C")
        elif origem == "Apenas Entradas":
            self.lbl_resumo_in.configure(text=f"Total Entradas: R$ {self.total_in:.2f}", text_color="#2ECC71")
            self.lbl_resumo_out.configure(text="")
            self.lbl_resumo_apagar.configure(text="")
            self.lbl_resumo_areceber.configure(text="")
        elif origem == "Apenas Saídas":
            self.lbl_resumo_in.configure(text="")
            self.lbl_resumo_out.configure(text=f"Total Saídas: R$ {self.total_out:.2f}", text_color="#E74C3C")
            self.lbl_resumo_apagar.configure(text="")
            self.lbl_resumo_areceber.configure(text="")
        elif origem == "Contas a Pagar":
            self.lbl_resumo_in.configure(text="")
            self.lbl_resumo_out.configure(text="")
            self.lbl_resumo_apagar.configure(text=f"Total a Pagar: R$ {self.total_boletos:.2f}")
            self.lbl_resumo_areceber.configure(text="")
        elif origem == "Contas a Receber":
            self.lbl_resumo_in.configure(text="")
            self.lbl_resumo_out.configure(text="")
            self.lbl_resumo_apagar.configure(text="")
            self.lbl_resumo_areceber.configure(text=f"Total a Receber: R$ {self.total_receber:.2f}", text_color="#1ABC9C")
        elif origem == "Todos os Cartões":
            self.lbl_resumo_in.configure(text=f"Total Gasto em Todos os Cartões: R$ {self.total_cartao:.2f}", text_color="#8A2BE2")
            self.lbl_resumo_out.configure(text="")
            self.lbl_resumo_apagar.configure(text="")
            self.lbl_resumo_areceber.configure(text="")
        else:
            self.lbl_resumo_in.configure(text=f"Total Gasto neste Cartão: R$ {self.total_cartao:.2f}", text_color="#8A2BE2")
            self.lbl_resumo_out.configure(text="")
            self.lbl_resumo_apagar.configure(text="")
            self.lbl_resumo_areceber.configure(text="")

    def abrir_popup_edicao(self, dados_movimentacao):
        id_mov, data_mov, tipo, conta, desc, valor, cat = dados_movimentacao
        
        popup = ctk.CTkToplevel(self)
        popup.title("Editar Lançamento")
        popup.geometry("380x450")
        popup.attributes("-topmost", True)
        popup.grab_set()

        ctk.CTkLabel(popup, text=f"Editando Registro #{id_mov}", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 10))

        ctk.CTkLabel(popup, text="Data (DD/MM/AAAA):").pack(anchor="w", padx=40)
        ent_data = ctk.CTkEntry(popup, width=300)
        ent_data.insert(0, data_mov.strftime('%d/%m/%Y'))
        ent_data.pack(padx=40, pady=(0, 10))

        ctk.CTkLabel(popup, text="Descrição:").pack(anchor="w", padx=40)
        ent_desc = ctk.CTkEntry(popup, width=300)
        ent_desc.insert(0, desc)
        ent_desc.pack(padx=40, pady=(0, 10))

        ctk.CTkLabel(popup, text="Valor (R$):").pack(anchor="w", padx=40)
        ent_valor = ctk.CTkEntry(popup, width=300)
        ent_valor.insert(0, str(valor))
        ent_valor.pack(padx=40, pady=(0, 20))

        def salvar_alteracoes():
            try:
                nova_data = datetime.strptime(ent_data.get().strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                novo_valor = float(ent_valor.get().replace(',', '.').strip())
                nova_desc = ent_desc.get().strip()
                
                sucesso, msg = banco.atualizar_movimentacao(id_mov, nova_data, tipo, conta, nova_desc, novo_valor, cat)
                
                if sucesso:
                    messagebox.showinfo("Sucesso", "Registro atualizado com sucesso!")
                    popup.destroy()
                    self.buscar_historico() 
                else:
                    messagebox.showerror("Erro", msg)
                    
            except ValueError:
                messagebox.showerror("Erro", "Formato de data ou valor inválido.")

        def excluir_registro():
            resposta = messagebox.askyesno("Cuidado", "Deseja realmente apagar este lançamento do histórico?")
            if resposta:
                sucesso, msg = banco.deletar_movimentacao(id_mov)
                if sucesso:
                    popup.destroy()
                    self.buscar_historico()
                else:
                    messagebox.showerror("Erro", msg)

        ctk.CTkButton(popup, text="Salvar Alterações", fg_color="green", hover_color="darkgreen", command=salvar_alteracoes).pack(pady=10)
        ctk.CTkButton(popup, text="Excluir Lançamento", fg_color="transparent", border_width=1, border_color="red", text_color="red", hover_color="gray20", command=excluir_registro).pack(pady=5)

    # ==========================================
    # GERAÇÃO DE RELATÓRIOS (PDF e EXCEL) OTIMIZADOS
    # ==========================================

    def gerar_pdf(self):
        if not PDF_DISPONIVEL:
            messagebox.showerror("Biblioteca Faltando", "A biblioteca ReportLab não está instalada. Digite: pip install reportlab")
            return

        if not self.dados_atuais:
            messagebox.showwarning("Aviso", "Não há dados na tela. Faça uma busca primeiro.")
            return

        caminho_arquivo = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Arquivos PDF", "*.pdf")], title="Salvar Relatório PDF")
        if not caminho_arquivo: return

        origem = self.combo_origem.get()
        d_ini_br = self.entry_data_ini.get()
        d_fim_br = self.entry_data_fim.get()

        try:
            cnv = canvas.Canvas(caminho_arquivo, pagesize=A4)
            pag = 1
            
            def desenhar_cabecalho(c, pagina):
                y = A4[1] - 20*mm
                
                c.setFont("Helvetica-Bold", 16)
                c.setFillColor(black)
                c.drawCentredString(A4[0]/2, y, "RELATÓRIO FINANCEIRO GERAL")
                y -= 8*mm
                
                c.setFont("Helvetica", 10)
                c.drawCentredString(A4[0]/2, y, f"Período Analisado: {d_ini_br} a {d_fim_br}")
                y -= 6*mm
                
                c.drawCentredString(A4[0]/2, y, f"Filtro Aplicado: {origem} | Categoria: {self.combo_categoria.get()}")
                y -= 10*mm

                # Cabeçalhos da tabela
                c.setFont("Helvetica-Bold", 9)
                c.drawString(15*mm, y, "DATA")
                c.drawString(35*mm, y, "TIPO")
                c.drawString(65*mm, y, "DESCRIÇÃO")
                c.drawString(135*mm, y, "CATEGORIA")
                c.drawRightString(A4[0] - 15*mm, y, "VALOR (R$)")
                y -= 3*mm
                
                c.setStrokeColor(black)
                c.line(15*mm, y, A4[0] - 15*mm, y)
                y -= 5*mm
                
                return y

            y = desenhar_cabecalho(cnv, pag)
            linha_idx = 0
            cor_fundo_linha = HexColor("#F5F5F5")

            # Agora todos os dados (incluindo boletos e a receber) já estão em self.dados_atuais
            itens_para_imprimir = list(self.dados_atuais)
            
            # Ordenar por data
            itens_para_imprimir.sort(key=lambda x: x[1])

            for mov in itens_para_imprimir:
                id_mov, data_mov, tipo, conta, desc, valor, cat = mov

                # Cria nova página se estiver acabando o espaço
                if y < 25*mm:
                    cnv.setFillColor(black)
                    cnv.setFont("Helvetica", 8)
                    cnv.drawRightString(A4[0] - 15*mm, 10*mm, f"Página {pag}")
                    cnv.drawString(15*mm, 10*mm, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                    cnv.showPage()
                    pag += 1
                    y = desenhar_cabecalho(cnv, pag)

                # Efeito Zebra (fundo cinza)
                if linha_idx % 2 == 0:
                    cnv.setFillColor(cor_fundo_linha)
                    cnv.rect(15*mm, y - 1.5*mm, A4[0] - 30*mm, 4.5*mm, fill=1, stroke=0)

                data_br = data_mov.strftime('%d/%m/%Y')
                desc_abrev = desc[:35] + "..." if len(desc) > 35 else desc
                cat_abrev = cat[:25] + "..." if len(cat) > 25 else cat
                tipo_abrev = tipo[:12] + "." if len(tipo) > 12 else tipo

                # Lógica de Cores do PDF
                if tipo == "ENTRADA": cor_texto = green; sinal = "+"
                elif tipo == "SAIDA": cor_texto = red; sinal = "-"
                elif tipo == "A PAGAR": cor_texto = HexColor("#F39C12"); sinal = "-"
                elif tipo == "A RECEBER": cor_texto = HexColor("#1ABC9C"); sinal = "+"
                else: cor_texto = HexColor("#8A2BE2"); sinal = "-" # Cartões

                cnv.setFont("Helvetica", 8)
                cnv.setFillColor(black)
                cnv.drawString(15*mm, y, data_br)
                
                cnv.setFillColor(cor_texto)
                cnv.drawString(35*mm, y, tipo_abrev)
                
                cnv.setFillColor(black)
                cnv.drawString(65*mm, y, desc_abrev)
                cnv.drawString(135*mm, y, cat_abrev)

                cnv.setFillColor(cor_texto)
                cnv.drawRightString(A4[0] - 15*mm, y, f"{sinal} R$ {valor:,.2f}")

                y -= 5*mm
                linha_idx += 1

            # ==========================================
            # BLOCO DE RESUMO FINAL NO PDF
            # ==========================================
            altura_box = 50*mm  # Aumentei levemente para caber o A Receber
            if y < (altura_box + 15*mm):
                cnv.setFillColor(black)
                cnv.setFont("Helvetica", 8)
                cnv.drawRightString(A4[0] - 15*mm, 10*mm, f"Página {pag}")
                cnv.drawString(15*mm, 10*mm, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                cnv.showPage()
                pag += 1
                y = A4[1] - 20*mm

            y -= 5*mm
            cnv.setStrokeColor(black)
            cnv.line(15*mm, y, A4[0] - 15*mm, y)
            y -= 10*mm

            # Desenha a caixa cinza de fundo
            y_inicio_box = y
            cnv.setFillColor(HexColor("#F9F9F9"))
            cnv.setStrokeColor(black)
            cnv.rect(15*mm, y_inicio_box - altura_box + 5*mm, 100*mm, altura_box, fill=1, stroke=1)

            y -= 2*mm
            cnv.setFont("Helvetica-Bold", 12)
            cnv.setFillColor(black)
            cnv.drawString(20*mm, y, "RESUMO DO PERÍODO:")

            y -= 8*mm
            cnv.setFont("Helvetica-Bold", 10)
            
            if origem == "Visão Geral":
                cnv.setFillColor(green)
                cnv.drawString(20*mm, y, "Total de Entradas:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_in:,.2f}")
                y -= 6*mm
                cnv.setFillColor(red)
                cnv.drawString(20*mm, y, "Total de Saídas:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_out:,.2f}")
                y -= 6*mm
                saldo = self.total_in - self.total_out
                cnv.setFillColor(green if saldo >= 0 else red)
                cnv.drawString(20*mm, y, "Saldo Líquido:")
                cnv.drawRightString(110*mm, y, f"R$ {saldo:,.2f}")
                y -= 8*mm
                cnv.setFillColor(HexColor("#F39C12"))
                cnv.drawString(20*mm, y, "Total A Pagar:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_boletos:,.2f}")
                y -= 6*mm
                cnv.setFillColor(HexColor("#1ABC9C"))
                cnv.drawString(20*mm, y, "Total A Receber:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_receber:,.2f}")
            elif origem == "Apenas Entradas":
                cnv.setFillColor(green)
                cnv.drawString(20*mm, y, "Total de Entradas:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_in:,.2f}")
            elif origem == "Apenas Saídas":
                cnv.setFillColor(red)
                cnv.drawString(20*mm, y, "Total de Saídas:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_out:,.2f}")
            elif origem == "Contas a Pagar":
                cnv.setFillColor(HexColor("#F39C12"))
                cnv.drawString(20*mm, y, "Total A Pagar:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_boletos:,.2f}")
            elif origem == "Contas a Receber":
                cnv.setFillColor(HexColor("#1ABC9C"))
                cnv.drawString(20*mm, y, "Total A Receber:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_receber:,.2f}")
            else:
                cnv.setFillColor(HexColor("#8A2BE2"))
                cnv.drawString(20*mm, y, "Total Gasto em Cartão:")
                cnv.drawRightString(110*mm, y, f"R$ {self.total_cartao:,.2f}")

            # Rodapé da última página
            cnv.setFillColor(black)
            cnv.setFont("Helvetica", 8)
            cnv.drawRightString(A4[0] - 15*mm, 10*mm, f"Página {pag}")
            cnv.drawString(15*mm, 10*mm, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

            cnv.save()
            
            # Abre o PDF automaticamente
            try:
                os.startfile(os.path.abspath(caminho_arquivo))
            except:
                pass
            
            messagebox.showinfo("Sucesso", "Relatório PDF gerado com sucesso!")

        except Exception as e:
            messagebox.showerror("Erro PDF", f"Falha ao gerar o arquivo:\n{str(e)}")

    def gerar_excel(self):
        if not EXCEL_DISPONIVEL:
            messagebox.showerror("Biblioteca Faltando", "A biblioteca Pandas não está instalada. Digite: pip install pandas openpyxl")
            return

        if not self.dados_atuais:
            messagebox.showwarning("Aviso", "Não há dados na tela para gerar Excel.")
            return

        caminho_arquivo = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Arquivos Excel", "*.xlsx")], title="Salvar Planilha Excel")
        if not caminho_arquivo: return

        origem = self.combo_origem.get()

        try:
            dados_formatados = []
            
            # Todos os dados (incluindo a pagar e a receber) já estão em self.dados_atuais
            for mov in self.dados_atuais:
                id_mov, data_mov, tipo, conta, desc, valor, cat = mov
                dados_formatados.append({
                    "Data": data_mov.strftime('%d/%m/%Y'),
                    "Tipo": tipo,
                    "Descrição": desc,
                    "Categoria": cat,
                    "Conta/Origem": conta,
                    "Valor": float(valor)
                })

            # Ordena e cria o DataFrame
            dados_formatados.sort(key=lambda x: datetime.strptime(x["Data"], '%d/%m/%Y'))
            df = pd.DataFrame(dados_formatados)

            # Usa o ExcelWriter e o openpyxl para gerar um Excel esteticamente bonito
            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Historico')
                worksheet = writer.sheets['Historico']

                from openpyxl.styles import Font, PatternFill, Alignment

                # Formatar o cabeçalho (Azul escuro, Letras brancas, Negrito, Centralizado)
                header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
                header_font = Font(color="FFFFFF", bold=True)
                for col in range(1, len(df.columns) + 1):
                    cell = worksheet.cell(row=1, column=col)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")

                # Ajustar Largura das Colunas
                larguras = {"A": 12, "B": 15, "C": 40, "D": 25, "E": 20, "F": 18}
                for letra, larg in larguras.items():
                    worksheet.column_dimensions[letra].width = larg

                # Formatar linhas de dados (Moeda e Cores por Tipo)
                for row in range(2, len(df) + 2):
                    celula_valor = worksheet[f"F{row}"]
                    celula_valor.number_format = '"R$" #,##0.00'
                    
                    celula_tipo = worksheet[f"B{row}"]
                    if celula_tipo.value in ["ENTRADA", "A RECEBER"]:
                        celula_tipo.font = Font(color="00B050", bold=True)
                    elif celula_tipo.value in ["SAIDA", "A PAGAR"]:
                        celula_tipo.font = Font(color="FF0000", bold=True)
                    else:
                        celula_tipo.font = Font(color="7030A0", bold=True) # Roxo para Cartões

                # ==========================================
                # CRIAR O QUADRO DE RESUMO (Pula 2 linhas)
                # ==========================================
                linha_inicio_resumo = len(df) + 4
                worksheet[f"C{linha_inicio_resumo}"] = "RESUMO FINANCEIRO"
                worksheet[f"C{linha_inicio_resumo}"].font = Font(bold=True, size=12, color="1F4E78")

                def add_linha_resumo(linha, texto, valor, cor="000000"):
                    worksheet[f"D{linha}"] = texto
                    worksheet[f"D{linha}"].font = Font(bold=True)
                    worksheet[f"D{linha}"].alignment = Alignment(horizontal="right")
                    
                    worksheet[f"E{linha}"] = valor
                    worksheet[f"E{linha}"].number_format = '"R$" #,##0.00'
                    worksheet[f"E{linha}"].font = Font(bold=True, color=cor)

                lin = linha_inicio_resumo + 1
                if origem == "Visão Geral":
                    add_linha_resumo(lin, "Total Entradas:", self.total_in, "00B050")
                    add_linha_resumo(lin + 1, "Total Saídas:", self.total_out, "FF0000")
                    
                    saldo = self.total_in - self.total_out
                    cor_saldo = "00B050" if saldo >= 0 else "FF0000"
                    add_linha_resumo(lin + 2, "Saldo Líquido:", saldo, cor_saldo)
                    
                    add_linha_resumo(lin + 3, "A Pagar:", self.total_boletos, "E26B0A") 
                    add_linha_resumo(lin + 4, "A Receber:", self.total_receber, "00B050") 
                elif origem == "Apenas Entradas":
                    add_linha_resumo(lin, "Total Entradas:", self.total_in, "00B050")
                elif origem == "Apenas Saídas":
                    add_linha_resumo(lin, "Total Saídas:", self.total_out, "FF0000")
                elif origem == "Contas a Pagar":
                    add_linha_resumo(lin, "Total A Pagar:", self.total_boletos, "E26B0A")
                elif origem == "Contas a Receber":
                    add_linha_resumo(lin, "Total A Receber:", self.total_receber, "00B050")
                else:
                    add_linha_resumo(lin, "Total Gasto (Cartões):", self.total_cartao, "7030A0")

            # Abre o Excel automaticamente (para o Windows)
            try:
                os.startfile(os.path.abspath(caminho_arquivo))
            except:
                pass
                
            messagebox.showinfo("Sucesso", "Planilha Excel gerada e formatada com sucesso!")

        except Exception as e:
            messagebox.showerror("Erro ao Gerar Excel", f"Falha: {str(e)}")