import customtkinter as ctk
import tkinter.messagebox as messagebox
import banco
from datetime import datetime
from dateutil.relativedelta import relativedelta

class TelaCartoes(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1) # Coluna dos Cartões
        self.grid_columnconfigure(1, weight=2) # Coluna da Fatura Detalhada
        self.grid_rowconfigure(1, weight=1)

        # Paleta de cores mapeada para o CustomTkinter
        self.cores_map = {
            "purple": "#8A2BE2", "orange": "#FF8C00", "blue": "#1E90FF",
            "red": "#DC143C", "green": "#2E8B57", "grey": "#808080",
            "cyan": "#00CED1", "amber": "#FFC107", "pink": "#FF69B4"
        }

        self.cartao_selecionado = None
        self.mes_fatura = datetime.today().month
        self.ano_fatura = datetime.today().year

        # --- CABEÇALHO ---
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(self.frame_top, text="Gestão de Cartões", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(self.frame_top, text="+ Novo Cartão", fg_color="#8A2BE2", hover_color="#6A1B9A", command=self.abrir_modal_cartao).pack(side="right")

        # --- LADO ESQUERDO: LISTA DE CARTÕES ---
        self.frame_cartoes = ctk.CTkScrollableFrame(self)
        self.frame_cartoes.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        # --- LADO DIREITO: FATURA DETALHADA ---
        self.frame_fatura = ctk.CTkFrame(self)
        self.frame_fatura.grid(row=1, column=1, sticky="nsew")
        self.frame_fatura.grid_columnconfigure(0, weight=1)
        self.frame_fatura.grid_rowconfigure(2, weight=1)

        # Cabeçalho da Fatura
        self.fatura_header = ctk.CTkFrame(self.frame_fatura, fg_color="transparent")
        self.fatura_header.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        
        self.btn_mes_ant = ctk.CTkButton(self.fatura_header, text="<", width=40, command=lambda: self.mudar_mes(-1))
        self.btn_mes_ant.pack(side="left")
        
        self.lbl_fatura_titulo = ctk.CTkLabel(self.fatura_header, text="Selecione um Cartão", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_fatura_titulo.pack(side="left", expand=True)

        self.btn_mes_prox = ctk.CTkButton(self.fatura_header, text=">", width=40, command=lambda: self.mudar_mes(1))
        self.btn_mes_prox.pack(side="right")

        # Painel de Valor da Fatura
        self.painel_valor = ctk.CTkFrame(self.frame_fatura)
        self.painel_valor.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        self.lbl_fatura_total = ctk.CTkLabel(self.painel_valor, text="R$ 0.00", font=ctk.CTkFont(size=30, weight="bold"))
        self.lbl_fatura_total.pack(pady=15)

        # Lista de Compras
        self.lista_compras = ctk.CTkScrollableFrame(self.frame_fatura, fg_color="transparent")
        self.lista_compras.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        # Botões de Ação da Fatura
        self.frame_acoes_fatura = ctk.CTkFrame(self.frame_fatura, fg_color="transparent")
        self.frame_acoes_fatura.grid(row=3, column=0, sticky="ew", padx=20, pady=15)
        self.frame_acoes_fatura.grid_columnconfigure((0,1), weight=1)

        self.btn_add_compra = ctk.CTkButton(self.frame_acoes_fatura, text="+ Adicionar Compra", state="disabled", command=self.abrir_modal_compra)
        self.btn_add_compra.grid(row=0, column=0, padx=5, sticky="ew")

        self.btn_fechar_fatura = ctk.CTkButton(self.frame_acoes_fatura, text="Fechar Fatura", fg_color="#D32F2F", hover_color="#B71C1C", state="disabled", command=self.fechar_fatura)
        self.btn_fechar_fatura.grid(row=0, column=1, padx=5, sticky="ew")

    # Mágica Compartilhada: Previsão Inteligente da Fatura Alvo
    def prever_fatura_alvo(self, data_digitada, dia_fechamento, cartao_id):
        if data_digitada.day >= dia_fechamento:
            fat = data_digitada + relativedelta(months=1)
        else:
            fat = data_digitada
            
        # Pula as faturas fechadas ou pagas para não bloquear o lançamento
        while banco.is_fatura_fechada(cartao_id, fat.month, fat.year):
            fat += relativedelta(months=1)
            
        return fat

    # ==========================================
    # LÓGICA DOS CARTÕES
    # ==========================================
    def carregar_cartoes(self):
        for widget in self.frame_cartoes.winfo_children():
            widget.destroy()

        cartoes = banco.listar_cartoes()
        
        # OTIMIZAÇÃO (O "PULO DO GATO"): Vai na nuvem apenas 1 vez para os limites
        sucesso, limites_bd = banco.executar_db("SELECT cartao_id, SUM(valor) FROM compras_cartao WHERE status IN ('ABERTA', 'FECHADA') GROUP BY cartao_id", fetchall=True)
        mapa_limites = {linha[0]: linha[1] for linha in limites_bd} if sucesso and limites_bd else {}

        if not cartoes:
            ctk.CTkLabel(self.frame_cartoes, text="Nenhum cartão cadastrado.", text_color="gray").pack(pady=20)
            return

        for cartao in cartoes:
            id_c, nome, lim_total, fech, venc, cor_nome = cartao
            cor_hex = self.cores_map.get(cor_nome, "#808080")
            
            # Limite Dinâmico puxado da memória
            consumido = mapa_limites.get(id_c, 0.0)
            lim_disp = float(lim_total) - float(consumido)

            card_frame = ctk.CTkFrame(self.frame_cartoes, fg_color=cor_hex, corner_radius=10)
            card_frame.pack(fill="x", padx=5, pady=5, ipadx=10, ipady=10)
            
            card_frame.bind("<Button-1>", lambda e, c=cartao: self.selecionar_cartao(c))

            top_row = ctk.CTkFrame(card_frame, fg_color="transparent")
            top_row.pack(fill="x")
            top_row.bind("<Button-1>", lambda e, c=cartao: self.selecionar_cartao(c))
            
            ctk.CTkLabel(top_row, text=nome, font=ctk.CTkFont(size=16, weight="bold"), text_color="white").pack(side="left")
            
            btn_edit = ctk.CTkButton(top_row, text="Editar", width=50, height=24, fg_color="transparent", border_width=1, border_color="white", text_color="white", command=lambda c=cartao: self.abrir_modal_cartao(c))
            btn_edit.pack(side="right")

            lbl_info = ctk.CTkLabel(card_frame, text=f"Disp: R$ {lim_disp:.2f} | Total: R$ {lim_total:.2f}\nFech: {fech} | Venc: {venc}", justify="left", text_color="white")
            lbl_info.pack(anchor="w", pady=(5,0))
            lbl_info.bind("<Button-1>", lambda e, c=cartao: self.selecionar_cartao(c))

    def selecionar_cartao(self, cartao):
        self.cartao_selecionado = cartao
        id_c, nome, lim, fech, venc, cor = cartao
        
        cor_hex = self.cores_map.get(cor, "#1E90FF")
        self.btn_add_compra.configure(state="normal", fg_color=cor_hex)
        
        hoje = datetime.today()
        # Abre o painel já prevendo qual é a fatura do momento
        fat_atual = self.prever_fatura_alvo(hoje, fech, id_c)
            
        self.mes_fatura = fat_atual.month
        self.ano_fatura = fat_atual.year
        
        self.carregar_fatura()

    def mudar_mes(self, delta):
        if not self.cartao_selecionado: return
        data_atual = datetime(self.ano_fatura, self.mes_fatura, 1) + relativedelta(months=delta)
        self.mes_fatura = data_atual.month
        self.ano_fatura = data_atual.year
        self.carregar_fatura()

    def carregar_fatura(self):
        if not self.cartao_selecionado: return
        id_c, nome, lim, fech, venc, cor = self.cartao_selecionado
        cor_hex = self.cores_map.get(cor, "#1E90FF")

        self.lbl_fatura_titulo.configure(text=f"{nome} - Fatura: {self.mes_fatura:02d}/{self.ano_fatura}")
        
        for w in self.lista_compras.winfo_children(): w.destroy()

        compras = banco.listar_compras_fatura(id_c, self.mes_fatura, self.ano_fatura)
        total = 0.0

        tem_aberta = False
        tem_fechada = False

        if not compras:
            ctk.CTkLabel(self.lista_compras, text="Nenhuma compra nesta fatura.", text_color="gray").pack(pady=20)
        else:
            for comp in compras:
                id_comp, desc_comp, val_comp, data_comp, cat_comp, status_comp = comp
                if status_comp in ['ABERTA', 'FECHADA']: 
                    total += val_comp
                
                if status_comp == 'ABERTA': tem_aberta = True
                if status_comp == 'FECHADA': tem_fechada = True

                cor_txt = "gray" if status_comp in ['FECHADA', 'PAGA'] else "white"
                simbolo = "🔒 " if status_comp in ['FECHADA', 'PAGA'] else ""

                item_frame = ctk.CTkFrame(self.lista_compras, fg_color="transparent")
                item_frame.pack(fill="x", pady=2)
                
                ctk.CTkLabel(item_frame, text=f"{simbolo}{desc_comp}\n{data_comp.strftime('%d/%m')} • {cat_comp}", justify="left", text_color=cor_txt).pack(side="left")
                
                if status_comp == 'ABERTA':
                    btn_ed = ctk.CTkButton(item_frame, text="✎", width=30, fg_color="transparent", command=lambda c=comp: self.abrir_modal_compra(c))
                    btn_ed.pack(side="right")
                
                ctk.CTkLabel(item_frame, text=f"R$ {val_comp:.2f}", font=ctk.CTkFont(weight="bold"), text_color=cor_txt).pack(side="right", padx=10)
                ctk.CTkFrame(self.lista_compras, height=1, fg_color="gray30").pack(fill="x", pady=5)

        self.lbl_fatura_total.configure(text=f"R$ {total:.2f}", text_color=cor_hex)

        if tem_aberta:
            self.btn_fechar_fatura.configure(text="Fechar Fatura", fg_color="#D32F2F", state="normal", command=self.fechar_fatura)
        elif tem_fechada:
            self.btn_fechar_fatura.configure(text="Reabrir Fatura", fg_color="#F57C00", state="normal", command=self.reabrir_fatura)
        else:
            self.btn_fechar_fatura.configure(text="Fechar Fatura", fg_color="gray", state="disabled")

    # ==========================================
    # MODAIS (CARTÃO E COMPRAS)
    # ==========================================
    def abrir_modal_cartao(self, cartao_dados=None):
        modal = ctk.CTkToplevel(self)
        modal.title("Novo Cartão" if not cartao_dados else "Editar Cartão")
        modal.geometry("350x520") 
        modal.grab_set()

        nome_var = ctk.StringVar(value=cartao_dados[1] if cartao_dados else "")
        lim_var = ctk.StringVar(value=str(cartao_dados[2]) if cartao_dados else "")
        fech_var = ctk.StringVar(value=str(cartao_dados[3]) if cartao_dados else "")
        venc_var = ctk.StringVar(value=str(cartao_dados[4]) if cartao_dados else "")
        cor_selecionada = cartao_dados[5] if cartao_dados else "purple"

        ctk.CTkLabel(modal, text="Nome do Cartão (Ex: Nubank)", anchor="w", text_color="gray").pack(padx=20, fill="x")
        ctk.CTkEntry(modal, textvariable=nome_var).pack(pady=(0, 10), padx=20, fill="x")
        
        ctk.CTkLabel(modal, text="Limite Total (R$)", anchor="w", text_color="gray").pack(padx=20, fill="x")
        ctk.CTkEntry(modal, textvariable=lim_var).pack(pady=(0, 10), padx=20, fill="x")
        
        row_labels = ctk.CTkFrame(modal, fg_color="transparent")
        row_labels.pack(fill="x", padx=20)
        ctk.CTkLabel(row_labels, text="Dia Fechamento", width=140, anchor="w", text_color="gray").pack(side="left")
        ctk.CTkLabel(row_labels, text="Dia Vencimento", width=140, anchor="w", text_color="gray").pack(side="right")
        
        row_datas = ctk.CTkFrame(modal, fg_color="transparent")
        row_datas.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkEntry(row_datas, textvariable=fech_var, width=140).pack(side="left")
        ctk.CTkEntry(row_datas, textvariable=venc_var, width=140).pack(side="right")

        ctk.CTkLabel(modal, text="Cor do Cartão:").pack(pady=(10,5))
        frame_cores = ctk.CTkFrame(modal, fg_color="transparent")
        frame_cores.pack(pady=5)

        botoes_cores = []
        def selecionar_cor(nome_cor):
            nonlocal cor_selecionada
            cor_selecionada = nome_cor
            for btn, n_cor in botoes_cores:
                btn.configure(border_width=3 if n_cor == nome_cor else 0, border_color="white")

        linha1 = ctk.CTkFrame(frame_cores, fg_color="transparent")
        linha1.pack()
        linha2 = ctk.CTkFrame(frame_cores, fg_color="transparent")
        linha2.pack()

        for i, (nome_cor, hex_cor) in enumerate(self.cores_map.items()):
            linha = linha1 if i < 5 else linha2
            btn = ctk.CTkButton(linha, text="", width=30, height=30, fg_color=hex_cor, hover_color=hex_cor, corner_radius=15, command=lambda c=nome_cor: selecionar_cor(c))
            btn.pack(side="left", padx=5, pady=5)
            botoes_cores.append((btn, nome_cor))
        
        selecionar_cor(cor_selecionada)

        def salvar():
            try:
                if cartao_dados:
                    banco.atualizar_cartao(cartao_dados[0], nome_var.get().strip(), lim_var.get().replace(',','.'), fech_var.get(), venc_var.get(), cor_selecionada)
                else:
                    banco.adicionar_cartao(nome_var.get().strip(), lim_var.get().replace(',','.'), fech_var.get(), venc_var.get(), cor_selecionada)
                self.carregar_cartoes()
                modal.destroy()
            except Exception as e:
                messagebox.showerror("Erro", "Verifique se todos os campos estão preenchidos corretamente.")

        def deletar():
            if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este cartão?"):
                banco.deletar_cartao(cartao_dados[0])
                self.cartao_selecionado = None
                self.carregar_cartoes()
                for w in self.lista_compras.winfo_children(): w.destroy()
                self.lbl_fatura_total.configure(text="R$ 0.00")
                modal.destroy()

        frame_botoes = ctk.CTkFrame(modal, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20, pady=20)
        
        if cartao_dados:
            ctk.CTkButton(frame_botoes, text="Excluir", fg_color="#D32F2F", hover_color="#B71C1C", command=deletar).pack(side="left", expand=True, padx=5)
        
        ctk.CTkButton(frame_botoes, text="Salvar", command=salvar).pack(side="right", expand=True, padx=5)

    def abrir_modal_compra(self, compra_dados=None):
        if not self.cartao_selecionado: return
        idc, nome_c, lim, fech, venc, cor = self.cartao_selecionado
        cor_hex = self.cores_map.get(cor, "#1E90FF")

        modal = ctk.CTkToplevel(self)
        modal.title("Nova Compra" if not compra_dados else "Editar Compra")
        modal.geometry("350x620") 
        modal.grab_set()

        hoje = datetime.today()
        # Calcula a previsão inteligente da fatura alvo
        fat_calc = self.prever_fatura_alvo(hoje, fech, idc)

        desc_var = ctk.StringVar(value=compra_dados[1] if compra_dados else "")
        val_var = ctk.StringVar(value=f"{compra_dados[2]:.2f}" if compra_dados else "")
        data_var = ctk.StringVar(value=compra_dados[3].strftime('%d/%m/%Y') if compra_dados else hoje.strftime('%d/%m/%Y'))
        parc_var = ctk.StringVar(value="1")
        
        m_fat = self.mes_fatura if compra_dados else fat_calc.month
        a_fat = self.ano_fatura if compra_dados else fat_calc.year
        fat_var = ctk.StringVar(value=f"{m_fat:02d}/{a_fat}")

        ctk.CTkLabel(modal, text="O que você comprou?", anchor="w", text_color="gray").pack(padx=20, fill="x")
        ctk.CTkEntry(modal, textvariable=desc_var).pack(pady=(0, 10), padx=20, fill="x")

        ctk.CTkLabel(modal, text="Valor Total (R$)", anchor="w", text_color="gray").pack(padx=20, fill="x")
        ctk.CTkEntry(modal, textvariable=val_var).pack(pady=(0, 10), padx=20, fill="x")
        
        ctk.CTkLabel(modal, text="Data (DD/MM/AAAA)", anchor="w", text_color="gray").pack(padx=20, fill="x")
        entry_data = ctk.CTkEntry(modal, textvariable=data_var)
        entry_data.pack(pady=(0, 10), padx=20, fill="x")
        
        if not compra_dados:
            ctk.CTkLabel(modal, text="Quantidade de Parcelas", anchor="w", text_color="gray").pack(padx=20, fill="x")
            ctk.CTkEntry(modal, textvariable=parc_var).pack(pady=(0, 10), padx=20, fill="x")
            
        ctk.CTkLabel(modal, text="Fatura Alvo (MM/AAAA)", anchor="w", text_color="gray").pack(padx=20, fill="x")
        entry_fatura = ctk.CTkEntry(modal, textvariable=fat_var)
        entry_fatura.pack(pady=(0, 10), padx=20, fill="x")

        # EVENTO ON_CHANGE (Inteligência do Flet trazida para o Desktop)
        def ao_digitar_data(event):
            if compra_dados: return # Na edição manual, não forçamos a mudança
            texto = entry_data.get().strip()
            if len(texto) == 10:
                try:
                    d_digitada = datetime.strptime(texto, '%d/%m/%Y')
                    nova_fat = self.prever_fatura_alvo(d_digitada, fech, idc)
                    fat_var.set(nova_fat.strftime('%m/%Y'))
                except ValueError:
                    pass 

        entry_data.bind("<KeyRelease>", ao_digitar_data)

        cats = banco.listar_categorias_por_tipo('SAIDA') or ["Geral"]
        cat_padrao = compra_dados[4] if compra_dados else cats[0]
        
        ctk.CTkLabel(modal, text="Categoria", anchor="w", text_color="gray").pack(padx=20, fill="x")
        drop_cat = ctk.CTkComboBox(modal, values=cats)
        drop_cat.set(cat_padrao)
        drop_cat.pack(pady=(0, 10), padx=20, fill="x")

        def salvar():
            try:
                v = float(val_var.get().replace(',', '.'))
                d = datetime.strptime(data_var.get().strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                m, a = fat_var.get().split('/')
                
                if compra_dados:
                    s, m_err = banco.atualizar_compra_cartao(compra_dados[0], desc_var.get(), v, d, drop_cat.get(), m, a)
                else:
                    p = int(parc_var.get())
                    s, m_err = banco.adicionar_compra_cartao(idc, desc_var.get(), v, d, p, drop_cat.get(), m, a)
                    
                if s:
                    self.carregar_fatura()
                    self.carregar_cartoes()
                    modal.destroy()
                else:
                    messagebox.showwarning("Aviso", m_err)
            except Exception as e:
                messagebox.showerror("Erro", "Verifique datas (DD/MM/AAAA) e valores.")

        def deletar():
            if messagebox.askyesno("Confirmar", "Apagar esta compra?"):
                banco.deletar_compra_cartao(compra_dados[0])
                self.carregar_fatura()
                self.carregar_cartoes()
                modal.destroy()

        frame_botoes = ctk.CTkFrame(modal, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20, pady=20)
        
        if compra_dados:
            ctk.CTkButton(frame_botoes, text="Excluir", fg_color="#D32F2F", hover_color="#B71C1C", command=deletar).pack(side="left", expand=True, padx=5)
        
        ctk.CTkButton(frame_botoes, text="Salvar Compra", fg_color=cor_hex, command=salvar).pack(side="right", expand=True, padx=5)

    def fechar_fatura(self):
        if messagebox.askyesno("Atenção", "Ao fechar a fatura, o total será enviado para 'A Pagar'. Confirmar?"):
            suc, msg = banco.fechar_fatura_cartao(self.cartao_selecionado[0], self.mes_fatura, self.ano_fatura)
            if suc:
                messagebox.showinfo("Sucesso", msg)
                self.carregar_fatura()
                self.carregar_cartoes()
            else:
                messagebox.showerror("Erro", msg)

    def reabrir_fatura(self):
        suc, msg = banco.reabrir_fatura_cartao(self.cartao_selecionado[0], self.mes_fatura, self.ano_fatura)
        if suc:
            messagebox.showinfo("Sucesso", msg)
            self.carregar_fatura()
            self.carregar_cartoes()
        else:
            messagebox.showerror("Erro", msg)