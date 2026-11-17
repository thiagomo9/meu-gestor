import customtkinter as ctk
import tkinter.messagebox as messagebox
import banco

class TelaCategorias(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        lbl_titulo = ctk.CTkLabel(self, text="Gerenciador de Contas e Categorias", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(pady=(20, 10))

        # ==========================================
        # CONFIGURAÇÃO DE ABAS
        # ==========================================
        self.tabview = ctk.CTkTabview(self, width=600, height=500)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.aba_bancos = self.tabview.add("Bancos (Contas)")
        self.aba_entradas = self.tabview.add("Receitas (Entradas)")
        self.aba_saidas = self.tabview.add("Despesas (Saídas)")

        self.construir_aba(self.aba_bancos, "BANCO")
        self.construir_aba(self.aba_entradas, "ENTRADA")
        self.construir_aba(self.aba_saidas, "SAIDA")

    def construir_aba(self, frame_pai, tipo_categoria):
        """Constrói os elementos visuais dentro da aba selecionada."""
        frame_top = ctk.CTkFrame(frame_pai, fg_color="transparent")
        frame_top.pack(fill="x", pady=10, padx=10)
        
        # Textos e cores dinâmicas baseadas na aba
        if tipo_categoria == "BANCO":
            placeholder = "Digite o nome do novo Banco"
            cor_btn, cor_hover = "#2980B9", "#1A5276"  # Azul
        elif tipo_categoria == "ENTRADA":
            placeholder = "Digite a nova categoria"
            cor_btn, cor_hover = "#27AE60", "#1E8449"  # Verde
        else:
            placeholder = "Digite a nova categoria"
            cor_btn, cor_hover = "#E74C3C", "#C0392B"  # Vermelho

        entry_nova = ctk.CTkEntry(frame_top, placeholder_text=placeholder, width=300)
        entry_nova.pack(side="left", padx=(0, 10))
        
        btn_add = ctk.CTkButton(
            frame_top, 
            text="Adicionar", 
            width=100, 
            fg_color=cor_btn, hover_color=cor_hover,
            command=lambda: self.salvar_nova(entry_nova, tipo_categoria, scroll_lista)
        )
        btn_add.pack(side="left")
        
        scroll_lista = ctk.CTkScrollableFrame(frame_pai)
        scroll_lista.pack(fill="both", expand=True, padx=10)
        
        self.carregar_lista(scroll_lista, tipo_categoria)

    # ==========================================
    # LÓGICA E BANCO DE DADOS
    # ==========================================

    def salvar_nova(self, entry, tipo_categoria, scroll_associado):
        # Categorias ficam em Maiúsculas, Bancos usamos as primeiras letras maiúsculas (Title)
        if tipo_categoria == 'BANCO':
            nome = entry.get().strip().title()
        else:
            nome = entry.get().strip().upper()
        
        if nome:
            if tipo_categoria == 'BANCO':
                try:
                    banco.executar_db("INSERT INTO contas_bancarias (usuario_id, nome) VALUES (%s, %s)", (banco.USUARIO_ID, nome))
                    sucesso, msg = True, "Banco adicionado com sucesso."
                except Exception as e:
                    sucesso, msg = False, f"Erro: {e}"
            else:
                sucesso, msg = banco.adicionar_categoria(nome, tipo_categoria)
                
            if sucesso:
                entry.delete(0, 'end')
                self.carregar_lista(scroll_associado, tipo_categoria)
            else:
                messagebox.showerror("Erro", msg)
        else:
            messagebox.showwarning("Aviso", "O nome não pode estar vazio.")

    def carregar_lista(self, scroll, tipo_categoria):
        """Carrega a lista do banco e cria apenas o botão de edição."""
        for widget in scroll.winfo_children():
            widget.destroy()
            
        if tipo_categoria == 'BANCO':
            itens = banco.listar_contas_bancarias() or []
        else:
            itens = banco.listar_categorias_por_tipo(tipo_categoria) or []
        
        for item in itens:
            linha = ctk.CTkFrame(scroll, fg_color="gray15")
            linha.pack(fill="x", pady=2)
            
            ctk.CTkLabel(linha, text=item, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15, pady=8)
            
            # Apenas o Botão de Editar visível na lista (UI Limpa)
            ctk.CTkButton(
                linha, 
                text="Editar", 
                width=60, 
                fg_color="gray30", hover_color="gray40",
                command=lambda c=item: self.abrir_popup_editar(c, scroll, tipo_categoria)
            ).pack(side="right", padx=15, pady=8)

    def abrir_popup_editar(self, nome_antigo, scroll, tipo_categoria):
        """Abre uma janela flutuante para renomear ou excluir o item selecionado."""
        popup = ctk.CTkToplevel(self)
        
        titulo_janela = "Editar Banco" if tipo_categoria == 'BANCO' else "Editar Categoria"
        cor_tema = "#2980B9" if tipo_categoria == 'BANCO' else "#E67E22"
        cor_hover = "#1A5276" if tipo_categoria == 'BANCO' else "#D35400"
        
        popup.title(titulo_janela)
        popup.geometry("380x320")
        popup.attributes("-topmost", True)
        popup.grab_set()

        ctk.CTkLabel(popup, text=titulo_janela, font=ctk.CTkFont(size=18, weight="bold"), text_color=cor_tema).pack(pady=(20, 5))
        ctk.CTkLabel(popup, text=f"Atual: {nome_antigo}", text_color="gray").pack(pady=(0, 15))
        
        ctk.CTkLabel(popup, text="Novo Nome:").pack(anchor="w", padx=50)
        entry_novo_nome = ctk.CTkEntry(popup, width=280)
        entry_novo_nome.insert(0, nome_antigo)
        entry_novo_nome.pack(pady=(0, 10))

        def confirmar_edicao():
            if tipo_categoria == 'BANCO':
                nome_novo = entry_novo_nome.get().strip().title()
            else:
                nome_novo = entry_novo_nome.get().strip().upper()
                
            if not nome_novo or nome_novo == nome_antigo:
                popup.destroy()
                return
                
            if tipo_categoria == 'BANCO':
                try:
                    banco.executar_db("UPDATE contas_bancarias SET nome = %s WHERE nome = %s AND usuario_id = %s", (nome_novo, nome_antigo, banco.USUARIO_ID))
                    sucesso, msg = True, "Banco renomeado com sucesso!"
                except Exception as e:
                    sucesso, msg = False, str(e)
            else:
                # Chama a função que atualiza a categoria e todos os lançamentos vinculados
                sucesso, msg = banco.editar_categoria_inteligente(nome_antigo, nome_novo, tipo_categoria)
            
            if sucesso:
                messagebox.showinfo("Sucesso", msg)
                self.carregar_lista(scroll, tipo_categoria)
                popup.destroy()
            else:
                messagebox.showerror("Erro do Banco", msg)

        def confirmar_exclusao():
            texto_aviso = "apagar este banco" if tipo_categoria == 'BANCO' else "apagar esta categoria"
            confirmacao = messagebox.askyesno(
                "Exclusão", 
                f"Você tem certeza que deseja {texto_aviso} '{nome_antigo}'?\n\n(Itens com lançamentos vinculados podem ser bloqueados por segurança)."
            )
            
            if confirmacao:
                if tipo_categoria == 'BANCO':
                    try:
                        banco.executar_db("DELETE FROM contas_bancarias WHERE nome = %s AND usuario_id = %s", (nome_antigo, banco.USUARIO_ID))
                        sucesso, msg = True, "Banco excluído com sucesso!"
                    except Exception as e:
                        sucesso, msg = False, f"Falha na exclusão. Podem existir lançamentos vinculados a este banco. Erro: {e}"
                else:
                    # Chama a função inteligente que bloqueia a exclusão se houver dados
                    sucesso, msg = banco.remover_categoria_segura(nome_antigo, tipo_categoria)
                    
                if sucesso:
                    self.carregar_lista(scroll, tipo_categoria)
                    popup.destroy()
                else:
                    messagebox.showwarning("Aviso de Segurança", msg)

        # Botão de Salvar Alterações
        ctk.CTkButton(
            popup, text="Salvar Novo Nome", fg_color=cor_tema, hover_color=cor_hover, command=confirmar_edicao
        ).pack(pady=(15, 5))
        
        # Botão de Excluir (escondido dentro do menu de edição)
        texto_btn_excluir = "Excluir Banco" if tipo_categoria == 'BANCO' else "Excluir Categoria"
        ctk.CTkButton(
            popup, text=texto_btn_excluir, fg_color="transparent", border_width=1, border_color="red", 
            text_color="red", hover_color="gray20", command=confirmar_exclusao
        ).pack(pady=5)