import customtkinter as ctk
import tkinter.messagebox as messagebox
import banco

class TelaConfigs(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Usamos um ScrollableFrame principal para caber tudo em qualquer resolução
        self.scroll_main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_main.pack(fill="both", expand=True, padx=20, pady=20)

        lbl_titulo = ctk.CTkLabel(self.scroll_main, text="Configurações e Perfil", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=(0, 20))

        # ==========================================
        # 1. MEU PERFIL (MESMA LÓGICA DO MOBILE)
        # ==========================================
        self.frame_perfil = ctk.CTkFrame(self.scroll_main, corner_radius=10)
        self.frame_perfil.pack(fill="x", pady=10)

        ctk.CTkLabel(self.frame_perfil, text="Meu Perfil", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2980B9").pack(anchor="w", padx=20, pady=(15, 5))
        
        # Simulação de Avatar e Nome
        info_perfil = ctk.CTkFrame(self.frame_perfil, fg_color="transparent")
        info_perfil.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(info_perfil, text="👤", font=ctk.CTkFont(size=40)).pack(side="left", padx=(0, 15))
        
        dados_usuario = ctk.CTkFrame(info_perfil, fg_color="transparent")
        dados_usuario.pack(side="left")
        ctk.CTkLabel(dados_usuario, text="Logado como:", text_color="gray").pack(anchor="w")
        
        # Fallback de segurança caso a variável ainda não esteja preenchida
        nome_exibicao = banco.USUARIO_NOME if banco.USUARIO_NOME else "Usuário"
        ctk.CTkLabel(dados_usuario, text=nome_exibicao, font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")

        btn_editar_perfil = ctk.CTkButton(
            self.frame_perfil, text="Editar Perfil",
            fg_color="#2980B9", hover_color="#1A5276", command=self.abrir_editar_perfil
        )
        btn_editar_perfil.pack(anchor="w", padx=20, pady=(0, 20))

        # ==========================================
        # 2. APARÊNCIA E SISTEMA
        # ==========================================
        self.frame_aparencia = ctk.CTkFrame(self.scroll_main, corner_radius=10)
        self.frame_aparencia.pack(fill="x", pady=10)

        ctk.CTkLabel(self.frame_aparencia, text="Aparência", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(15, 10))

        row_tema = ctk.CTkFrame(self.frame_aparencia, fg_color="transparent")
        row_tema.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(row_tema, text="Tema do Aplicativo:", width=150, anchor="w").pack(side="left")
        self.opt_tema = ctk.CTkOptionMenu(row_tema, values=["Dark", "Light", "System"], command=self.mudar_tema)
        self.opt_tema.set("Dark")
        self.opt_tema.pack(side="left", padx=10)

        row_escala = ctk.CTkFrame(self.frame_aparencia, fg_color="transparent")
        row_escala.pack(fill="x", padx=20, pady=(5, 20))
        ctk.CTkLabel(row_escala, text="Escala da Interface:", width=150, anchor="w").pack(side="left")
        self.opt_escala = ctk.CTkOptionMenu(row_escala, values=["80%", "90%", "100%", "110%", "120%"], command=self.mudar_escala)
        self.opt_escala.set("100%")
        self.opt_escala.pack(side="left", padx=10)

        # ==========================================
        # 3. INFORMAÇÕES DO SISTEMA
        # ==========================================
        self.frame_info = ctk.CTkFrame(self.scroll_main, corner_radius=10)
        self.frame_info.pack(fill="x", pady=10)

        ctk.CTkLabel(self.frame_info, text="Informações do Sistema", font=ctk.CTkFont(size=16, weight="bold"), text_color="gray").pack(anchor="w", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(self.frame_info, text="💻 Desenvolvedor: Thiago Oliveira").pack(anchor="w", padx=20, pady=2)
        ctk.CTkLabel(self.frame_info, text="📞 Suporte WhatsApp: (79) 98149-1530").pack(anchor="w", padx=20, pady=(2, 20))

        # ==========================================
        # 4. PAINEL DE AUDITORIA (SÓ PARA O DEV/ADMIN)
        # ==========================================
        # A VERIFICAÇÃO CORRETA: Checar se o ROLE do usuário logado é ADMIN no banco de dados.
        if banco.USUARIO_ROLE == 'ADMIN':
            self.frame_dev = ctk.CTkFrame(self.scroll_main, corner_radius=10, border_width=1, border_color="#8E44AD")
            self.frame_dev.pack(fill="x", pady=10)

            ctk.CTkLabel(self.frame_dev, text="Área Restrita (Desenvolvedor)", font=ctk.CTkFont(size=16, weight="bold"), text_color="#8E44AD").pack(anchor="w", padx=20, pady=(15, 5))
            ctk.CTkLabel(self.frame_dev, text="Acesso a logs de usuários e segurança do banco de dados.", text_color="gray").pack(anchor="w", padx=20)
            
            btn_auditoria = ctk.CTkButton(
                self.frame_dev, text="Painel de Auditoria", 
                fg_color="#8E44AD", hover_color="#732D91", command=self.abrir_painel_auditoria
            )
            btn_auditoria.pack(anchor="w", padx=20, pady=(10, 20))

        # ==========================================
        # 5. BOTÃO DE SAIR
        # ==========================================
        btn_sair = ctk.CTkButton(
            self.scroll_main, text="SAIR DA CONTA", font=ctk.CTkFont(weight="bold"),
            fg_color="#C0392B", hover_color="#922B21", height=40, command=self.sair_da_conta
        )
        btn_sair.pack(pady=30)


    # ==========================================
    # LÓGICA DE INTERFACE
    # ==========================================
    def mudar_tema(self, novo_tema):
        ctk.set_appearance_mode(novo_tema)

    def mudar_escala(self, nova_escala):
        escala_float = int(nova_escala.replace("%", "")) / 100
        ctk.set_widget_scaling(escala_float)

    def sair_da_conta(self):
        resposta = messagebox.askyesno("Sair", "Tem certeza que deseja encerrar a sessão?")
        if resposta:
            # Destrói a janela principal e orienta o usuário
            janela_principal = self.winfo_toplevel()
            janela_principal.destroy()

    # ==========================================
    # EDIÇÃO DE PERFIL
    # ==========================================
    def abrir_editar_perfil(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Editar Perfil")
        popup.geometry("400x450")
        popup.attributes("-topmost", True)
        popup.grab_set()

        try:
            email_atual = banco.obter_email_usuario()
        except:
            email_atual = "" # Fallback caso a função ainda não exista

        ctk.CTkLabel(popup, text="Editar Dados da Conta", font=ctk.CTkFont(size=18, weight="bold"), text_color="#2980B9").pack(pady=(20, 15))

        ctk.CTkLabel(popup, text="E-mail:").pack(anchor="w", padx=40)
        ent_email = ctk.CTkEntry(popup, width=320)
        ent_email.insert(0, email_atual)
        ent_email.pack(padx=40, pady=(0, 15))

        ctk.CTkLabel(popup, text="Nova Senha (deixe em branco para não alterar):").pack(anchor="w", padx=40)
        ent_senha = ctk.CTkEntry(popup, width=320, show="*")
        ent_senha.pack(padx=40, pady=(0, 15))

        ctk.CTkLabel(popup, text="Confirmar Nova Senha:").pack(anchor="w", padx=40)
        ent_confirma = ctk.CTkEntry(popup, width=320, show="*")
        ent_confirma.pack(padx=40, pady=(0, 20))

        def salvar_perfil():
            novo_email = ent_email.get().strip()
            senha = ent_senha.get()
            confirma = ent_confirma.get()
            
            if not novo_email:
                messagebox.showwarning("Aviso", "O E-mail não pode ficar vazio!")
                return

            if senha or confirma:
                if senha != confirma:
                    messagebox.showerror("Erro", "As senhas não coincidem!")
                    return
                if len(senha) < 4:
                    messagebox.showwarning("Aviso", "A senha deve ter pelo menos 4 caracteres.")
                    return
                
                try:
                    sucesso, msg = banco.atualizar_perfil(novo_email, senha)
                except:
                    sucesso, msg = False, "Erro ao chamar banco.atualizar_perfil. Verifique o banco.py"
            else:
                try:
                    sucesso, msg = banco.atualizar_perfil(novo_email)
                except:
                    sucesso, msg = False, "Erro ao chamar banco.atualizar_perfil. Verifique o banco.py"

            if sucesso:
                messagebox.showinfo("Sucesso", "Perfil atualizado com sucesso!")
                popup.destroy()
            else:
                messagebox.showerror("Erro", msg)

        ctk.CTkButton(popup, text="Salvar Alterações", fg_color="#27AE60", hover_color="#1E8449", command=salvar_perfil).pack(pady=10)

    # ==========================================
    # PAINEL DE AUDITORIA (DEV)
    # ==========================================
    def abrir_painel_auditoria(self):
        popup_audit = ctk.CTkToplevel(self)
        popup_audit.title("Auditoria e Segurança")
        popup_audit.geometry("700x500")
        popup_audit.attributes("-topmost", True)
        popup_audit.grab_set()

        ctk.CTkLabel(popup_audit, text="Painel de Controle do Desenvolvedor", font=ctk.CTkFont(size=20, weight="bold"), text_color="#8E44AD").pack(pady=(20, 10))

        tabs_audit = ctk.CTkTabview(popup_audit, width=650, height=400)
        tabs_audit.pack(padx=20, pady=10, fill="both", expand=True)

        aba_usuarios = tabs_audit.add("Usuários Cadastrados")
        aba_logs = tabs_audit.add("Logs de Acesso")

        # --- 1. PREENCHENDO ABA USUÁRIOS ---
        scroll_users = ctk.CTkScrollableFrame(aba_usuarios)
        scroll_users.pack(fill="both", expand=True, padx=10, pady=10)

        # Checa se a função existe no banco.
        if hasattr(banco, "listar_todos_usuarios"):
            lista_users = banco.listar_todos_usuarios()
        else:
            lista_users = [
                ("ID", "Nome (Exemplo)", "Email (Exemplo)", "Login"),
                ("⚠️", "Aviso ao Dev", "Crie a função 'listar_todos_usuarios()' no banco.py", "-")
            ]

        for u in lista_users:
            linha = ctk.CTkFrame(scroll_users, fg_color="gray15")
            linha.pack(fill="x", pady=2)
            
            ctk.CTkLabel(linha, text=f"ID: {u[0]}", width=50, text_color="#8E44AD", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=5)
            ctk.CTkLabel(linha, text=f"{u[1]}", width=150, anchor="w").grid(row=0, column=1, padx=5, pady=5)
            ctk.CTkLabel(linha, text=f"{u[2]}", width=200, anchor="w", text_color="gray").grid(row=0, column=2, padx=5, pady=5)
            ctk.CTkLabel(linha, text=f"@{u[3]}", width=100, anchor="w").grid(row=0, column=3, padx=5, pady=5)

        # --- 2. PREENCHENDO ABA LOGS ---
        scroll_logs = ctk.CTkScrollableFrame(aba_logs)
        scroll_logs.pack(fill="both", expand=True, padx=10, pady=10)

        if hasattr(banco, "listar_logs_acesso"):
            lista_logs = banco.listar_logs_acesso()
        else:
            lista_logs = [
                ("Data/Hora", "Usuário ID", "Ação Realizada"),
                ("Agora", "1", "Login efetuado com sucesso (Exemplo)"),
                ("⚠️", "-", "Crie a função 'listar_logs_acesso()' no banco.py para ver logs reais.")
            ]

        for log in lista_logs:
            linha_log = ctk.CTkFrame(scroll_logs, fg_color="gray15")
            linha_log.pack(fill="x", pady=2)
            
            ctk.CTkLabel(linha_log, text=f"{log[0]}", width=150, anchor="w").grid(row=0, column=0, padx=10, pady=5)
            ctk.CTkLabel(linha_log, text=f"User ID: {log[1]}", width=80, anchor="w", text_color="#2980B9").grid(row=0, column=1, padx=5, pady=5)
            ctk.CTkLabel(linha_log, text=f"{log[2]}", width=350, anchor="w").grid(row=0, column=2, padx=5, pady=5)