import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime
import banco 

class TelaCaixa(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # ==========================================
        # ESTRUTURA PRINCIPAL DE COLUNAS E LINHAS
        # ==========================================
        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=2) 
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # FRAME ESQUERDO: NOVO LANÇAMENTO
        # ==========================================
        self.frame_cadastro = ctk.CTkFrame(self, corner_radius=10)
        self.frame_cadastro.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        lbl_titulo_cad = ctk.CTkLabel(self.frame_cadastro, text="Novo Lançamento", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo_cad.pack(pady=(20, 20))

        # --- Entrada do Tipo (Entrada / Saída) ---
        ctk.CTkLabel(self.frame_cadastro, text="Tipo de Movimentação:").pack(anchor="w", padx=20)
        self.var_tipo = ctk.StringVar(value="ENTRADA")
        
        self.seg_tipo = ctk.CTkSegmentedButton(
            self.frame_cadastro, 
            values=["ENTRADA", "SAIDA"], 
            variable=self.var_tipo, 
            command=self.atualizar_categorias
        )
        self.seg_tipo.pack(padx=20, pady=(0, 15), fill="x")

        # --- Entrada da Data ---
        ctk.CTkLabel(self.frame_cadastro, text="Data (DD/MM/AAAA):").pack(anchor="w", padx=20)
        
        self.entry_data = ctk.CTkEntry(self.frame_cadastro)
        self.entry_data.insert(0, datetime.today().strftime('%d/%m/%Y'))
        self.entry_data.pack(padx=20, pady=(0, 10), fill="x")

        # --- Entrada da Descrição ---
        ctk.CTkLabel(self.frame_cadastro, text="Descrição:").pack(anchor="w", padx=20)
        
        self.entry_desc = ctk.CTkEntry(self.frame_cadastro)
        self.entry_desc.pack(padx=20, pady=(0, 10), fill="x")

        # --- Entrada do Valor ---
        ctk.CTkLabel(self.frame_cadastro, text="Valor (R$):").pack(anchor="w", padx=20)
        
        self.entry_valor = ctk.CTkEntry(self.frame_cadastro)
        self.entry_valor.pack(padx=20, pady=(0, 10), fill="x")

        # --- Seleção da Conta Bancária ---
        ctk.CTkLabel(self.frame_cadastro, text="Conta/Carteira:").pack(anchor="w", padx=20)
        
        bancos = banco.listar_contas_bancarias()
        if not bancos:
            bancos = ["Sem Cadastro"]
            
        self.combo_conta = ctk.CTkComboBox(self.frame_cadastro, values=bancos)
        self.combo_conta.pack(padx=20, pady=(0, 10), fill="x")

        # --- Seleção da Categoria ---
        ctk.CTkLabel(self.frame_cadastro, text="Categoria:").pack(anchor="w", padx=20)
        
        self.combo_categoria = ctk.CTkComboBox(self.frame_cadastro, values=[])
        self.combo_categoria.pack(padx=20, pady=(0, 25), fill="x")

        # --- Botão de Salvar ---
        self.btn_salvar = ctk.CTkButton(
            self.frame_cadastro, 
            text="Registrar no Caixa", 
            command=self.salvar_movimentacao, 
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_salvar.pack(pady=10, padx=20, fill="x")

        # ==========================================
        # FRAME DIREITO: DASHBOARD E EXTRATO
        # ==========================================
        self.frame_direito = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_direito.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")

        # --- Container dos Cards ---
        self.frame_cards = ctk.CTkFrame(self.frame_direito, fg_color="transparent")
        self.frame_cards.pack(fill="x", pady=(0, 15))
        self.frame_cards.grid_columnconfigure((0, 1, 2), weight=1)

        # Card de Entradas
        card_in = ctk.CTkFrame(self.frame_cards, fg_color="#1E3A2F", corner_radius=8)
        card_in.grid(row=0, column=0, padx=5, sticky="nsew")
        ctk.CTkLabel(card_in, text="RECEITAS", text_color="#A9DFBF", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10,0))
        self.lbl_total_entradas = ctk.CTkLabel(card_in, text="R$ 0.00", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_total_entradas.pack(pady=(0,10))

        # Card de Saídas
        card_out = ctk.CTkFrame(self.frame_cards, fg_color="#4A2323", corner_radius=8)
        card_out.grid(row=0, column=1, padx=5, sticky="nsew")
        ctk.CTkLabel(card_out, text="DESPESAS", text_color="#F5B7B1", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10,0))
        self.lbl_total_saidas = ctk.CTkLabel(card_out, text="R$ 0.00", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_total_saidas.pack(pady=(0,10))

        # Card de Saldo Total
        card_saldo = ctk.CTkFrame(self.frame_cards, fg_color="#1F4E5B", corner_radius=8)
        card_saldo.grid(row=0, column=2, padx=5, sticky="nsew")
        ctk.CTkLabel(card_saldo, text="SALDO DO MÊS", text_color="#A9CCE3", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10,0))
        self.lbl_saldo = ctk.CTkLabel(card_saldo, text="R$ 0.00", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_saldo.pack(pady=(0,10))

        # --- Lista de Extrato ---
        self.frame_lista = ctk.CTkFrame(self.frame_direito, corner_radius=10)
        self.frame_lista.pack(fill="both", expand=True)

        lbl_titulo_lista = ctk.CTkLabel(self.frame_lista, text="Extrato do Mês Atual", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_titulo_lista.pack(pady=(15, 10))

        # Cabeçalhos da Tabela
        cabecalho = ctk.CTkFrame(self.frame_lista, fg_color="transparent")
        cabecalho.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(cabecalho, text="Data", width=80, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(cabecalho, text="Descrição", width=180, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(cabecalho, text="Conta", width=100, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5)
        ctk.CTkLabel(cabecalho, text="Valor", width=100, anchor="e", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5)

        # Área de rolagem para o extrato
        self.scroll_extrato = ctk.CTkScrollableFrame(self.frame_lista)
        self.scroll_extrato.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Inicialização da tela
        self.atualizar_categorias("ENTRADA") 
        self.carregar_extrato()

    # ==========================================
    # MÉTODOS DE LÓGICA E INTERFACE
    # ==========================================

    def atualizar_categorias(self, tipo_selecionado):
        """Atualiza a lista de categorias baseada na escolha de Entrada ou Saída."""
        categorias = banco.listar_categorias_por_tipo(tipo_selecionado)
        
        if not categorias:
            categorias = ["Geral"]
            
        self.combo_categoria.configure(values=categorias)
        self.combo_categoria.set(categorias[0])
        
        if tipo_selecionado == "ENTRADA":
            self.btn_salvar.configure(fg_color="green", hover_color="darkgreen")
        else:
            self.btn_salvar.configure(fg_color="#A93226", hover_color="#7B241C")

    def salvar_movimentacao(self):
        """Coleta os dados dos campos e salva no banco de dados."""
        tipo = self.var_tipo.get()
        data_str = self.entry_data.get().strip()
        desc = self.entry_desc.get().strip()
        valor_str = self.entry_valor.get().replace(',', '.').strip()
        conta = self.combo_conta.get()
        categoria = self.combo_categoria.get()

        # Validação de campos vazios
        if not desc or not valor_str or not data_str:
            messagebox.showwarning("Aviso", "Preencha a Data, Descrição e Valor!")
            return

        try:
            valor = float(valor_str)
            data_db = datetime.strptime(data_str, '%d/%m/%Y').strftime('%Y-%m-%d')
            
            sucesso, msg = banco.adicionar_movimentacao_avulsa(data_db, tipo, conta, desc, valor, categoria)
            
            if sucesso:
                self.entry_desc.delete(0, 'end')
                self.entry_valor.delete(0, 'end')
                self.carregar_extrato()
                messagebox.showinfo("Sucesso", "Lançamento registrado!")
            else:
                messagebox.showerror("Erro no Banco", msg)
                
        except ValueError:
            messagebox.showerror("Erro", "Formato de data ou valor inválido.")

    def carregar_extrato(self):
        """Carrega as movimentações do banco e as exibe na interface."""
        # Limpa os itens antigos da tela
        for widget in self.scroll_extrato.winfo_children():
            widget.destroy()
            
        hoje = datetime.today()
        movimentacoes = banco.listar_movimentacoes_mes(hoje.year, hoje.month)
        
        total_entradas = 0.0
        total_saidas = 0.0

        if not movimentacoes:
            ctk.CTkLabel(self.scroll_extrato, text="Sem movimentações.", text_color="gray").pack(pady=40)
        else:
            for mov in movimentacoes:
                data_mov, tipo, conta, desc, valor, cat = mov
                
                # Regras visuais baseadas no tipo de movimentação
                if tipo == 'ENTRADA':
                    total_entradas += valor
                    cor_valor = "#2ECC71"
                    sinal = "+ "
                else:
                    total_saidas += valor
                    cor_valor = "#E74C3C"
                    sinal = "- "

                # Cria a linha visual para a transação
                linha = ctk.CTkFrame(self.scroll_extrato, fg_color="transparent")
                linha.pack(fill="x", pady=2)
                
                data_br = data_mov.strftime('%d/%m/%Y')
                
                ctk.CTkLabel(linha, text=data_br, width=80, anchor="w").grid(row=0, column=0, padx=5)
                ctk.CTkLabel(linha, text=desc, width=180, anchor="w").grid(row=0, column=1, padx=5)
                ctk.CTkLabel(linha, text=conta, width=100, anchor="w").grid(row=0, column=2, padx=5)
                ctk.CTkLabel(linha, text=f"{sinal}R$ {valor:.2f}", width=100, anchor="e", text_color=cor_valor, font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5)

        # Atualiza os totais na parte superior da tela
        saldo = total_entradas - total_saidas
        self.lbl_total_entradas.configure(text=f"R$ {total_entradas:.2f}")
        self.lbl_total_saidas.configure(text=f"R$ {total_saidas:.2f}")
        
        # Cor do saldo
        if saldo < 0:
            cor_saldo = "#E74C3C"
        else:
            cor_saldo = "white"
            
        self.lbl_saldo.configure(text=f"R$ {saldo:.2f}", text_color=cor_saldo)

# ==========================================
# TESTE INDIVIDUAL (Opcional)
# ==========================================
if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("1000x650")
    frame = TelaCaixa(master=root)
    frame.pack(fill="both", expand=True)
    root.mainloop()