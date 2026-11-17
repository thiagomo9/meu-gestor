import customtkinter as ctk

# Importação de todas as telas modulares
from tela_login import TelaLogin
from tela_caixa import TelaCaixa
from tela_cartoes import TelaCartoes # <-- A NOVA TELA DE CARTÕES
from tela_contas_pagar import TelaContasPagar
from tela_contas_receber import TelaContasReceber
from tela_categorias import TelaCategorias
from tela_historico import TelaHistorico 
from tela_configs import TelaConfigs
import banco

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Gestor Financeiro Pessoal - Logado como: {banco.USUARIO_NOME}")
        
        # ==========================================
        # CONFIGURAÇÃO DE TELA CHEIA
        # ==========================================
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        self.geometry(f"{largura_tela}x{altura_tela}+0+0")

        def aplicar_zoom():
            try:
                self.state('zoomed')
            except:
                self.attributes('-zoomed', True)

        self.after(200, aplicar_zoom)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # MENU LATERAL (SIDEBAR) LIMPO
        # ==========================================
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(9, weight=1) 

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MEU GESTOR", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        self.sub_logo = ctk.CTkLabel(self.sidebar_frame, text=f"Bem-vindo(a), {banco.USUARIO_NOME}", font=ctk.CTkFont(size=12), text_color="gray")
        self.sub_logo.grid(row=1, column=0, padx=20, pady=(0, 30))

        # Botões de Navegação
        self.btn_caixa = ctk.CTkButton(self.sidebar_frame, text="Fluxo de Caixa", fg_color="transparent", anchor="w", command=self.mostrar_caixa)
        self.btn_caixa.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # ---> O NOVO BOTÃO DE CARTÕES AQUI (Logo após o Caixa) <---
        self.btn_cartoes = ctk.CTkButton(self.sidebar_frame, text="Cartões de Crédito", fg_color="transparent", anchor="w", command=self.mostrar_cartoes)
        self.btn_cartoes.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_contas = ctk.CTkButton(self.sidebar_frame, text="Contas a Pagar", fg_color="transparent", anchor="w", command=self.mostrar_contas)
        self.btn_contas.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.btn_receber = ctk.CTkButton(self.sidebar_frame, text="Contas a Receber", fg_color="transparent", anchor="w", command=self.mostrar_receber)
        self.btn_receber.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.btn_historico = ctk.CTkButton(self.sidebar_frame, text="Histórico e Relatórios", fg_color="transparent", anchor="w", command=self.mostrar_historico)
        self.btn_historico.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        self.btn_categorias = ctk.CTkButton(self.sidebar_frame, text="Categorias", fg_color="transparent", anchor="w", command=self.mostrar_categorias)
        self.btn_categorias.grid(row=7, column=0, padx=20, pady=10, sticky="ew")

        self.btn_configs = ctk.CTkButton(self.sidebar_frame, text="Configurações", fg_color="transparent", anchor="w", command=self.mostrar_configs)
        self.btn_configs.grid(row=8, column=0, padx=20, pady=10, sticky="ew")

        # ==========================================
        # GERENCIADOR DE TELAS (ÁREA DE CONTEÚDO)
        # ==========================================
        self.container_principal = ctk.CTkFrame(self, fg_color="transparent")
        self.container_principal.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.container_principal.grid_columnconfigure(0, weight=1)
        self.container_principal.grid_rowconfigure(0, weight=1)

        self.frames = {}
        # TelaCartoes adicionada na lista de inicialização
        for F in (TelaCaixa, TelaCartoes, TelaContasPagar, TelaContasReceber, TelaCategorias, TelaHistorico, TelaConfigs):
            nome_da_pagina = F.__name__
            frame = F(master=self.container_principal)
            self.frames[nome_da_pagina] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.mostrar_caixa()

    # ==========================================
    # LÓGICA DE NAVEGAÇÃO
    # ==========================================
    
    def mostrar_caixa(self):
        self.selecionar_botao(self.btn_caixa)
        self.frames["TelaCaixa"].tkraise()

    def mostrar_cartoes(self):
        self.selecionar_botao(self.btn_cartoes)
        self.frames["TelaCartoes"].carregar_cartoes() # Atualiza os dados sempre que abrir
        self.frames["TelaCartoes"].tkraise()

    def mostrar_contas(self):
        self.selecionar_botao(self.btn_contas)
        # Se sua TelaContasPagar tiver um método de recarregar, pode chamar aqui:
        # self.frames["TelaContasPagar"].carregar_dados() 
        self.frames["TelaContasPagar"].tkraise()

    def mostrar_receber(self):
        self.selecionar_botao(self.btn_receber)
        self.frames["TelaContasReceber"].tkraise()

    def mostrar_historico(self):
        self.selecionar_botao(self.btn_historico)
        self.frames["TelaHistorico"].tkraise()

    def mostrar_categorias(self):
        self.selecionar_botao(self.btn_categorias)
        self.frames["TelaCategorias"].tkraise()

    def mostrar_configs(self):
        self.selecionar_botao(self.btn_configs)
        self.frames["TelaConfigs"].tkraise()

    def selecionar_botao(self, botao_ativo):
        # A nova tela adicionada ao sistema de cores dos botões
        for btn in [self.btn_caixa, self.btn_cartoes, self.btn_contas, self.btn_receber, self.btn_historico, self.btn_categorias, self.btn_configs]:
            btn.configure(fg_color="transparent")
        botao_ativo.configure(fg_color=("gray75", "gray25"))

def abrir_sistema():
    app = AppPrincipal()
    app.mainloop()

if __name__ == "__main__":
    tela_login = TelaLogin(on_success=abrir_sistema)
    tela_login.mainloop()