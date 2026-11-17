import os
from dotenv import load_dotenv
import customtkinter as ctk
import tkinter.messagebox as messagebox
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import banco

# Carrega as variáveis do cofre
load_dotenv()

# ==========================================
# CREDENCIAIS DO SERVIDOR DE E-MAIL
# ==========================================
EMAIL_REMETENTE = os.getenv("EMAIL_USER")
SENHA_APP = os.getenv("EMAIL_PASS")

class TelaLogin(ctk.CTk):
# ... (o resto do código continua igual)
    def __init__(self, on_success):
        super().__init__()
        
        self.on_success = on_success 

        self.title("Acesso ao Sistema")
        self.geometry("400x600") # Aumentei um pouco a altura para caber o novo botão
        self.resizable(False, False)

        self.frame_login = ctk.CTkFrame(self, width=320, height=500, corner_radius=15)
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center")

        lbl_titulo = ctk.CTkLabel(self.frame_login, text="MEU GESTOR", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=(40, 10))
        
        lbl_sub = ctk.CTkLabel(self.frame_login, text="Acesso Restrito", font=ctk.CTkFont(size=14), text_color="gray")
        lbl_sub.pack(pady=(0, 30))

        self.entry_user = ctk.CTkEntry(self.frame_login, placeholder_text="Usuário", width=250, height=40)
        self.entry_user.pack(pady=10)

        self.entry_pass = ctk.CTkEntry(self.frame_login, placeholder_text="Senha", show="*", width=250, height=40)
        self.entry_pass.pack(pady=10)

        self.btn_entrar = ctk.CTkButton(self.frame_login, text="ENTRAR", width=250, height=40, font=ctk.CTkFont(weight="bold"), command=self.validar_acesso)
        self.btn_entrar.pack(pady=(20, 15))

        self.btn_recuperar = ctk.CTkButton(self.frame_login, text="Esqueci minha senha", fg_color="transparent", text_color="gray", hover_color="gray20", command=self.abrir_popup_recuperacao)
        self.btn_recuperar.pack(pady=(0, 10))

        # --- NOVO BOTÃO: Criar Conta ---
        self.btn_criar_conta = ctk.CTkButton(self.frame_login, text="Não tem uma conta? Cadastre-se", fg_color="transparent", text_color="#3498DB", hover_color="gray20", command=self.abrir_popup_cadastro)
        self.btn_criar_conta.pack(pady=(0, 20))

    # ==========================================
    # LÓGICA DE LOGIN
    # ==========================================
    def validar_acesso(self):
        usuario_digitado = self.entry_user.get().strip()
        senha_digitada = self.entry_pass.get().strip()

        sucesso, msg = banco.login_sistema(usuario_digitado, senha_digitada)
        
        if sucesso:
            self.destroy() 
            self.on_success() 
        else:
            messagebox.showerror("Acesso Negado", msg)

    # ==========================================
    # LÓGICA DE CADASTRO DE NOVO USUÁRIO
    # ==========================================
    def abrir_popup_cadastro(self):
        """Abre a janela para registrar um novo usuário."""
        popup = ctk.CTkToplevel(self)
        popup.title("Criar Nova Conta")
        popup.geometry("400x550")
        popup.attributes("-topmost", True)
        popup.grab_set() # Impede de clicar na janela de trás

        ctk.CTkLabel(popup, text="Crie sua Conta", font=ctk.CTkFont(weight="bold", size=20)).pack(pady=(20, 20))
        
        ent_nome = ctk.CTkEntry(popup, width=280, placeholder_text="Seu Nome Completo")
        ent_nome.pack(pady=10)

        ent_email = ctk.CTkEntry(popup, width=280, placeholder_text="Seu melhor E-mail")
        ent_email.pack(pady=10)

        ent_usuario = ctk.CTkEntry(popup, width=280, placeholder_text="Nome de Usuário (Login)")
        ent_usuario.pack(pady=10)

        ent_senha = ctk.CTkEntry(popup, width=280, placeholder_text="Crie uma Senha", show="*")
        ent_senha.pack(pady=10)

        ent_senha_conf = ctk.CTkEntry(popup, width=280, placeholder_text="Confirme a Senha", show="*")
        ent_senha_conf.pack(pady=10)

        def processar_cadastro():
            nome = ent_nome.get().strip()
            email = ent_email.get().strip()
            usuario = ent_usuario.get().strip()
            senha = ent_senha.get().strip()
            senha_conf = ent_senha_conf.get().strip()

            # Validações básicas
            if not nome or not email or not usuario or not senha:
                messagebox.showwarning("Atenção", "Por favor, preencha todos os campos.")
                return
            
            if senha != senha_conf:
                messagebox.showerror("Erro", "As senhas não coincidem. Tente novamente.")
                return
            
            if "@" not in email or "." not in email:
                messagebox.showerror("Erro", "Por favor, digite um formato de e-mail válido.")
                return

            # Chama a função no backend
            sucesso, msg = banco.registrar_novo_usuario(nome, email, usuario, senha)
            
            if sucesso:
                messagebox.showinfo("Sucesso", msg)
                popup.destroy() # Fecha a janela de cadastro
                # Preenche automaticamente o login para o usuário
                self.entry_user.delete(0, 'end')
                self.entry_user.insert(0, usuario)
            else:
                messagebox.showerror("Erro no Cadastro", msg)

        btn_salvar = ctk.CTkButton(popup, text="Concluir Cadastro", fg_color="#27AE60", hover_color="#1E8449", height=40, font=ctk.CTkFont(weight="bold"), command=processar_cadastro)
        btn_salvar.pack(pady=(20, 10))


    # ==========================================
    # LÓGICA DE RECUPERAÇÃO POR E-MAIL
    # ==========================================
    def abrir_popup_recuperacao(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Recuperar Senha")
        popup.geometry("350x250")
        popup.attributes("-topmost", True)
        popup.grab_set()

        ctk.CTkLabel(popup, text="Recuperação de Acesso", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=(20, 10))
        ctk.CTkLabel(popup, text="Digite o e-mail cadastrado na sua conta:").pack(pady=(0, 10))
        
        entry_email = ctk.CTkEntry(popup, width=280, placeholder_text="exemplo@gmail.com")
        entry_email.pack(pady=10)

        def processar_recuperacao():
            email_digitado = entry_email.get().strip()
            if not email_digitado:
                return

            sucesso, dados = banco.redefinir_senha_por_email(email_digitado)
            
            if sucesso:
                enviou = self.enviar_email(email_digitado, dados["nome"], dados["nova_senha"])
                if enviou:
                    messagebox.showinfo("E-mail Enviado", "Uma senha temporária foi enviada para o seu e-mail.")
                    popup.destroy()
                else:
                    messagebox.showerror("Erro SMTP", "Falha ao enviar o e-mail.")
            else:
                messagebox.showerror("Erro", dados) 

        ctk.CTkButton(popup, text="Enviar Senha Temporária", fg_color="#2980B9", command=processar_recuperacao).pack(pady=15)

    def enviar_email(self, email_destino, nome, nova_senha):
        assunto = "Recuperação de Senha - Meu Gestor"
        corpo = f"Olá, {nome}!\n\nVocê solicitou a recuperação de senha.\nSua nova senha é: {nova_senha}\n\nRecomendamos alterá-la."
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = email_destino
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain'))

        try:
            servidor = smtplib.SMTP('smtp.gmail.com', 587)
            servidor.starttls() 
            servidor.login(EMAIL_REMETENTE, SENHA_APP) 
            servidor.send_message(msg)
            servidor.quit()
            return True
        except:
            return False

# Teste Individual
if __name__ == "__main__":
    def abrir_sistema():
        print("Login com Sucesso!")
    app = TelaLogin(on_success=abrir_sistema)
    app.mainloop()