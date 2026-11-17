import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime
from dateutil.relativedelta import relativedelta  # <-- Mágica das datas
import banco 

class TelaContasPagar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=2) 
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # FRAME ESQUERDO: CADASTRO
        # ==========================================
        self.frame_cadastro = ctk.CTkFrame(self, corner_radius=10)
        self.frame_cadastro.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        lbl_titulo_cad = ctk.CTkLabel(self.frame_cadastro, text="Nova Conta a Pagar", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo_cad.pack(pady=(20, 20))

        ctk.CTkLabel(self.frame_cadastro, text="Descrição:").pack(anchor="w", padx=20)
        self.entry_desc = ctk.CTkEntry(self.frame_cadastro, width=250)
        self.entry_desc.pack(padx=20, pady=(0, 10))

        ctk.CTkLabel(self.frame_cadastro, text="Valor (R$):").pack(anchor="w", padx=20)
        self.entry_valor = ctk.CTkEntry(self.frame_cadastro, width=250)
        self.entry_valor.pack(padx=20, pady=(0, 10))

        ctk.CTkLabel(self.frame_cadastro, text="Vencimento:").pack(anchor="w", padx=20)
        self.entry_vencimento = ctk.CTkEntry(self.frame_cadastro, width=250)
        self.entry_vencimento.insert(0, datetime.today().strftime('%d/%m/%Y'))
        self.entry_vencimento.pack(padx=20, pady=(0, 10))

        ctk.CTkLabel(self.frame_cadastro, text="Categoria:").pack(anchor="w", padx=20)
        categorias_saida = banco.listar_categorias_por_tipo('SAIDA')
        
        if not categorias_saida:
            categorias_saida = ["Geral"]
            
        self.combo_categoria = ctk.CTkComboBox(self.frame_cadastro, values=categorias_saida, width=250)
        self.combo_categoria.pack(padx=20, pady=(0, 20))

        # --- NOVAS OPÇÕES DE REPETIÇÃO E PARCELAMENTO ---
        self.var_recorrente = ctk.BooleanVar(value=False)
        self.chk_recorrente = ctk.CTkCheckBox(
            self.frame_cadastro, 
            text="Repetir / Parcelar Lançamento", 
            variable=self.var_recorrente, 
            command=self.toggle_frequencia
        )
        self.chk_recorrente.pack(anchor="w", padx=20, pady=(0, 10))

        # Sub-frame oculto para as opções de recorrência
        self.frame_opcoes_rec = ctk.CTkFrame(self.frame_cadastro, fg_color="transparent")
        
        self.combo_frequencia = ctk.CTkComboBox(self.frame_opcoes_rec, values=["MENSAL", "SEMANAL", "ANUAL"], width=250)
        self.combo_frequencia.pack(padx=20, pady=(0, 10))
        
        ctk.CTkLabel(self.frame_opcoes_rec, text="Quantas vezes? (Em branco p/ infinito):", text_color="gray").pack(anchor="w", padx=20)
        self.entry_qtd_vezes = ctk.CTkEntry(self.frame_opcoes_rec, width=250)
        self.entry_qtd_vezes.pack(padx=20, pady=(0, 10))
        
        # Botão Salvar
        self.btn_salvar = ctk.CTkButton(self.frame_cadastro, text="Adicionar Conta", command=self.salvar_conta, fg_color="#E67E22", hover_color="#D35400")
        self.btn_salvar.pack(pady=20)

        # ==========================================
        # FRAME DIREITO: LISTA PENDENTES
        # ==========================================
        self.frame_lista = ctk.CTkFrame(self, corner_radius=10)
        self.frame_lista.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")

        lbl_titulo_lista = ctk.CTkLabel(self.frame_lista, text="Contas Pendentes", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo_lista.pack(pady=(20, 10))

        self.scroll_contas = ctk.CTkScrollableFrame(self.frame_lista)
        self.scroll_contas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.carregar_lista_contas()

    # ==========================================
    # LÓGICA E BANCO DE DADOS
    # ==========================================

    def toggle_frequencia(self):
        if self.var_recorrente.get():
            self.frame_opcoes_rec.pack(before=self.btn_salvar, fill="x")
        else:
            self.frame_opcoes_rec.pack_forget()

    def salvar_conta(self):
        desc = self.entry_desc.get().strip()
        valor_str = self.entry_valor.get().replace(',', '.').strip()
        venc_str = self.entry_vencimento.get().strip()
        cat = self.combo_categoria.get()
        
        recorrente = self.var_recorrente.get()
        freq = self.combo_frequencia.get() if recorrente else "MENSAL"
        qtd_str = self.entry_qtd_vezes.get().strip()

        try:
            valor = float(valor_str)
            venc_base = datetime.strptime(venc_str, '%d/%m/%Y')
            
            sucesso = False
            
            # LÓGICA 1: Parcelamento Finito (Ex: 5 vezes)
            if recorrente and qtd_str and qtd_str.isdigit():
                qtd = int(qtd_str)
                for i in range(qtd):
                    if freq == "MENSAL": nova_data = venc_base + relativedelta(months=i)
                    elif freq == "ANUAL": nova_data = venc_base + relativedelta(years=i)
                    elif freq == "SEMANAL": nova_data = venc_base + relativedelta(weeks=i)
                    else: nova_data = venc_base
                    
                    data_db = nova_data.strftime('%Y-%m-%d')
                    desc_final = f"{desc} ({i+1}/{qtd})"
                    
                    # Enviamos False para não virar um loop infinito no banco de dados
                    sucesso, msg = banco.adicionar_conta_pagar(desc_final, valor, data_db, cat, False, freq)
                    if not sucesso: break

            # LÓGICA 2: Infinito (Conta Fixa) ou Único
            else:
                is_infinita = recorrente and not qtd_str
                data_db = venc_base.strftime('%Y-%m-%d')
                sucesso, msg = banco.adicionar_conta_pagar(desc, valor, data_db, cat, is_infinita, freq)

            if sucesso:
                self.carregar_lista_contas()
                self.entry_desc.delete(0, 'end')
                self.entry_valor.delete(0, 'end')
                if recorrente:
                    self.entry_qtd_vezes.delete(0, 'end')
            else:
                messagebox.showerror("Erro do Banco", msg)
                
        except ValueError:
            messagebox.showerror("Erro de Validação", "A data ou o valor estão no formato incorreto.")

    def carregar_lista_contas(self):
        for widget in self.scroll_contas.winfo_children():
            widget.destroy()
            
        contas = banco.listar_contas_pendentes()
        
        if not contas:
            ctk.CTkLabel(self.scroll_contas, text="Nenhuma conta pendente! Tudo em dia. 🎉", text_color="gray").pack(pady=40)
            return

        for conta in contas:
            id_conta, desc, valor, vencimento_date, cat, rec, freq = conta
            
            if isinstance(vencimento_date, str):
                vencimento_date = datetime.strptime(vencimento_date, '%Y-%m-%d').date()

            cor_fundo = "gray15" if rec else "transparent"
            icone_desc = f"🔄 {desc}" if rec else desc
                
            linha = ctk.CTkFrame(self.scroll_contas, fg_color=cor_fundo)
            linha.pack(fill="x", pady=2)
            
            data_br = vencimento_date.strftime('%d/%m/%Y')
            cor_data = "#E74C3C" if vencimento_date < datetime.today().date() else "white"
            
            ctk.CTkLabel(linha, text=data_br, width=90, text_color=cor_data).grid(row=0, column=0, padx=5, pady=5)
            ctk.CTkLabel(linha, text=icone_desc, width=170, anchor="w").grid(row=0, column=1, padx=5, pady=5)
            ctk.CTkLabel(linha, text=f"R$ {valor:.2f}", width=80, font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=5)
            
            ctk.CTkButton(
                linha, text="Editar", width=60, fg_color="gray30", hover_color="gray40",
                command=lambda dados=conta: self.abrir_popup_edicao(dados)
            ).grid(row=0, column=3, padx=10, pady=5)

            ctk.CTkButton(
                linha, text="Pagar", width=60, fg_color="#27AE60", hover_color="#1E8449",
                command=lambda cid=id_conta, cdesc=desc, cval=valor: self.abrir_popup_pagamento(cid, cdesc, cval)
            ).grid(row=0, column=4, padx=5, pady=5)

    def abrir_popup_edicao(self, dados_conta):
        id_c, desc_c, valor_c, venc_c, cat_c, rec_c, freq_c = dados_conta
        
        if isinstance(venc_c, str): venc_c = datetime.strptime(venc_c, '%Y-%m-%d').date()

        popup = ctk.CTkToplevel(self)
        popup.title("Editar Vencimento")
        popup.geometry("380x520")
        popup.attributes("-topmost", True)
        popup.grab_set()

        ctk.CTkLabel(popup, text="Editar Conta a Pagar", font=ctk.CTkFont(size=18, weight="bold"), text_color="#E67E22").pack(pady=(15, 10))

        ctk.CTkLabel(popup, text="Descrição:").pack(anchor="w", padx=40)
        ent_desc = ctk.CTkEntry(popup, width=300)
        ent_desc.insert(0, desc_c)
        ent_desc.pack(padx=40, pady=(0, 10))

        ctk.CTkLabel(popup, text="Valor (R$):").pack(anchor="w", padx=40)
        ent_valor = ctk.CTkEntry(popup, width=300)
        ent_valor.insert(0, f"{valor_c:.2f}")
        ent_valor.pack(padx=40, pady=(0, 10))

        ctk.CTkLabel(popup, text="Data (DD/MM/AAAA):").pack(anchor="w", padx=40)
        ent_data = ctk.CTkEntry(popup, width=300)
        ent_data.insert(0, venc_c.strftime('%d/%m/%Y'))
        ent_data.pack(padx=40, pady=(0, 10))

        ctk.CTkLabel(popup, text="Categoria:").pack(anchor="w", padx=40)
        cats = banco.listar_categorias_por_tipo('SAIDA') or ["Geral"]
        combo_cat = ctk.CTkComboBox(popup, values=cats, width=300)
        combo_cat.set(cat_c if cat_c in cats else cats[0])
        combo_cat.pack(padx=40, pady=(0, 10))

        var_rec = ctk.BooleanVar(value=rec_c)
        chk_rec = ctk.CTkCheckBox(popup, text="Repetir nos próximos meses?", variable=var_rec, fg_color="#E67E22")
        chk_rec.pack(anchor="w", padx=40, pady=(10, 5))

        combo_freq = ctk.CTkComboBox(popup, values=["MENSAL", "SEMANAL", "ANUAL"], width=300)
        combo_freq.set(freq_c)
        combo_freq.pack(padx=40, pady=(0, 20))

        def salvar_edicao():
            desc = ent_desc.get().strip()
            val_str = ent_valor.get().replace(',', '.').strip()
            try:
                novo_valor = float(val_str)
                data_db = datetime.strptime(ent_data.get().strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                sucesso, msg = banco.atualizar_conta_pagar(id_c, desc, novo_valor, data_db, combo_cat.get(), var_rec.get(), combo_freq.get())
                if sucesso:
                    messagebox.showinfo("Sucesso", "Vencimento atualizado com sucesso!")
                    popup.destroy()
                    self.carregar_lista_contas()
                else: messagebox.showerror("Erro", msg)
            except ValueError:
                messagebox.showerror("Erro", "Verifique o formato do valor ou da data.")

        def excluir_boleto():
            if messagebox.askyesno("Excluir Boleto", f"Tem certeza que deseja apagar o boleto '{desc_c}'?"):
                sucesso, msg = banco.deletar_conta_pendente(id_c)
                if sucesso:
                    popup.destroy()
                    self.carregar_lista_contas()
                else: messagebox.showerror("Erro", msg)

        ctk.CTkButton(popup, text="Salvar Alterações", fg_color="#E67E22", hover_color="#D35400", command=salvar_edicao).pack(pady=5)
        ctk.CTkButton(popup, text="Excluir Boleto", fg_color="transparent", border_width=1, border_color="red", text_color="red", hover_color="gray20", command=excluir_boleto).pack(pady=5)

    def abrir_popup_pagamento(self, id_conta, descricao, valor_total):
        popup = ctk.CTkToplevel(self)
        popup.title("Efetuar Pagamento")
        popup.geometry("380x420")
        popup.attributes("-topmost", True)
        popup.grab_set()
        
        ctk.CTkLabel(popup, text=f"Dar Baixa: {descricao}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(popup, text=f"Dívida atual: R$ {valor_total:.2f}", text_color="gray").pack(pady=(0, 15))
        
        ctk.CTkLabel(popup, text="Data do Pagamento (DD/MM/AAAA):").pack(anchor="w", padx=40)
        ent_data = ctk.CTkEntry(popup, width=300)
        ent_data.insert(0, datetime.today().strftime('%d/%m/%Y'))
        ent_data.pack(padx=40, pady=(0, 10))

        ctk.CTkLabel(popup, text="Valor a Pagar (Para Parcial, digite menos):").pack(anchor="w", padx=40)
        ent_valor = ctk.CTkEntry(popup, width=300)
        ent_valor.insert(0, f"{valor_total:.2f}")
        ent_valor.pack(padx=40, pady=(0, 10))

        ctk.CTkLabel(popup, text="Pagar usando qual conta?").pack(anchor="w", padx=40)
        bancos = banco.listar_contas_bancarias()
        combo_banco = ctk.CTkComboBox(popup, values=bancos if bancos else ["Sem Cadastro"], width=300)
        combo_banco.pack(padx=40, pady=(0, 20))
        
        def confirmar():
            try:
                val_pago = float(ent_valor.get().replace(',', '.').strip())
                data_pag_db = datetime.strptime(ent_data.get().strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                origem = combo_banco.get()
                
                sucesso, msg = banco.processar_pagamento_conta(id_conta, origem, data_pag_db, val_pago)
                if sucesso:
                    messagebox.showinfo("Pagamento Registrado", msg)
                    popup.destroy()
                    self.carregar_lista_contas()
                else: messagebox.showerror("Erro ao Pagar", msg)
            except ValueError:
                messagebox.showerror("Erro de Validação", "Verifique o valor numérico e a data digitada!")
                
        ctk.CTkButton(popup, text="Confirmar Pagamento", command=confirmar, fg_color="#27AE60", hover_color="#1E8449").pack(pady=10)