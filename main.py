import flet as ft
import banco
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

async def main(page: ft.Page):
    # ==========================================
    # CONFIGURAÇÕES BASE DO APP
    # ==========================================
    page.title = "Meu Gestor"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 700

    def show_snack(msg, is_success=True):
        cor = ft.Colors.GREEN_800 if is_success else ft.Colors.RED_800
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=cor)
        page.snack_bar.open = True
        page.update()

    # ==========================================
    # SISTEMA DE NOTIFICAÇÃO
    # ==========================================
    def verificar_lembretes_vencimento():
        pendentes = banco.listar_contas_pendentes()
        hoje = datetime.today().date()
        contas_hoje = [c for c in pendentes if c[3] == hoje]
        contas_atrasadas = [c for c in pendentes if c[3] < hoje]

        if contas_hoje or contas_atrasadas:
            lista_msg = []
            if contas_hoje:
                lista_msg.append(f"⚠️ **Vencem hoje:** {', '.join([c[1] for c in contas_hoje])}")
            if contas_atrasadas:
                lista_msg.append(f"🚨 **Em atraso:** {', '.join([c[1] for c in contas_atrasadas])}")
            
            msg_final = "\n\n".join(lista_msg)

            def fechar_aviso(e):
                dlg_aviso.open = False
                page.update()

            dlg_aviso = ft.AlertDialog(
                title=ft.Text("Lembrete de Pagamentos"),
                content=ft.Text(msg_final),
                actions=[ft.TextButton("Entendido", on_click=fechar_aviso)]
            )
            page.overlay.append(dlg_aviso)
            dlg_aviso.open = True
            page.update()

    def calcular_saldo_mes():
        hoje = datetime.today()
        movimentacoes = banco.listar_movimentacoes_mes(hoje.year, hoje.month)
        total_entradas = sum(m[4] for m in movimentacoes if m[1] == 'ENTRADA') if movimentacoes else 0.0
        total_saidas = sum(m[4] for m in movimentacoes if m[1] == 'SAIDA') if movimentacoes else 0.0
        return total_entradas, total_saidas

    # Mágica Compartilhada: Previsão Inteligente da Fatura Alvo
    def prever_fatura_alvo(data_digitada, dia_fechamento, cartao_id):
        if data_digitada.day >= dia_fechamento:
            fat = data_digitada + relativedelta(months=1)
        else:
            fat = data_digitada
            
        while banco.is_fatura_fechada(cartao_id, fat.month, fat.year):
            fat += relativedelta(months=1)
            
        return fat

    # ==========================================
    # O CORAÇÃO DO APP (DASHBOARD E NAVEGAÇÃO)
    # ==========================================
    def construir_app_principal():
        area_conteudo = ft.Container(expand=True, alignment=ft.Alignment.TOP_CENTER, padding=20)

        txt_saldo_total = ft.Text(size=36, weight="bold")
        txt_receitas = ft.Text(size=16, color=ft.Colors.GREEN_400, weight="bold")
        txt_despesas = ft.Text(size=16, color=ft.Colors.RED_400, weight="bold")

        col_historico = ft.Column(scroll="auto", expand=True)
        col_vencimentos = ft.Column(spacing=10) 

        # --- FUNÇÃO UNIVERSAL DE PAGAMENTO ---
        def mostrar_modal_pagamento(id_conta, nome_conta, valor_conta):
            bancos_disp = banco.listar_contas_bancarias() or ["Dinheiro"]
            drop_conta_pag = ft.Dropdown(
                label="Pagar usando qual conta?", 
                options=[ft.dropdown.Option(b) for b in bancos_disp], 
                value=bancos_disp[0]
            )
            
            inp_valor_pagar = ft.TextField(
                label="Valor (Para Parcial, digite menos)", 
                value=f"{valor_conta:.2f}", 
                width=320, 
                keyboard_type=ft.KeyboardType.NUMBER
            )
            inp_data_pagamento = ft.TextField(
                label="Data do Pagamento (DD/MM/AAAA)", 
                value=datetime.today().strftime('%d/%m/%Y'), 
                width=320
            )
            
            def confirmar_pagamento(e_pag):
                e_pag.control.disabled = True
                e_pag.control.update()
                try:
                    val_pago = float(inp_valor_pagar.value.replace(',', '.').strip())
                    data_pag_db = datetime.strptime(inp_data_pagamento.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    
                    sucesso, msg = banco.processar_pagamento_conta(id_conta, drop_conta_pag.value, data_pag_db, val_pago)
                    
                    if sucesso:
                        bs_pag.open = False
                        atualizar_valores_globais()
                        show_snack(msg, True)
                    else:
                        show_snack(msg, False)
                        e_pag.control.disabled = False
                        e_pag.control.update()
                except ValueError:
                    show_snack("Verifique o valor e a data!", False)
                    e_pag.control.disabled = False
                    e_pag.control.update()

            btn_conf_pag = ft.Container(
                content=ft.Text("CONFIRMAR PAGAMENTO", color=ft.Colors.WHITE, weight="bold"), 
                bgcolor=ft.Colors.GREEN_600, width=320, height=50, border_radius=8, 
                alignment=ft.Alignment.CENTER, ink=True, on_click=confirmar_pagamento
            )
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text(f"Dar Baixa: {nome_conta}", size=20, weight="bold"), 
                    ft.Text(f"Dívida total: R$ {valor_conta:.2f}", size=14, color="gray"), 
                    inp_data_pagamento, 
                    inp_valor_pagar, 
                    drop_conta_pag, 
                    ft.Container(height=10), 
                    btn_conf_pag
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs_pag = ft.BottomSheet(bs_content)
            page.overlay.append(bs_pag)
            bs_pag.open = True
            page.update()

        # --- LÓGICA DO HISTÓRICO (FIXO EM 30 DIAS) ---
        def atualizar_historico():
            col_historico.controls.clear()
            hoje = datetime.today()
            
            data_ini = (hoje - timedelta(days=30)).strftime('%Y-%m-%d')
            data_fim = hoje.strftime('%Y-%m-%d')
            
            movs = banco.listar_historico_filtrado(data_ini, data_fim)
            t_ent = 0.0
            t_sai = 0.0

            if not movs:
                col_historico.controls.append(ft.Container(content=ft.Text("Nenhum registro encontrado nos últimos 30 dias.", color="gray"), padding=10))
            else:
                for m in movs:
                    id_m, data, tipo, conta, desc, valor, cat = m
                    cor = ft.Colors.GREEN_400 if tipo == 'ENTRADA' else ft.Colors.RED_400
                    icone = ft.Icons.ARROW_UPWARD if tipo == 'ENTRADA' else ft.Icons.ARROW_DOWNWARD
                    
                    if tipo == 'ENTRADA':
                        t_ent += valor
                    else:
                        t_sai += valor

                    item_lista = ft.ListTile(
                        leading=ft.Container(content=ft.Icon(icone, color=cor), padding=10, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=8),
                        title=ft.Text(desc, weight="bold"),
                        subtitle=ft.Text(f"{data.strftime('%d/%m/%Y')} • {cat}", size=12, color="gray"),
                        trailing=ft.Row([
                            ft.Text(f"R$ {valor:.2f}", color=cor, weight="bold", size=14),
                            ft.IconButton(ft.Icons.EDIT, icon_color="gray", tooltip="Editar", on_click=lambda e, m_obj=m: abrir_edicao_extrato(m_obj))
                        ], alignment=ft.MainAxisAlignment.END, tight=True)
                    )
                    col_historico.controls.append(item_lista)

                col_historico.controls.append(ft.Divider(height=20, color="transparent"))
                
                resumo_card = ft.Container(
                    content=ft.Column([
                        ft.Text("RESUMO (ÚLTIMOS 30 DIAS)", size=12, weight="bold", color="blue"),
                        ft.Row([ft.Text("Entradas:"), ft.Text(f"R$ {t_ent:.2f}", color="green", weight="bold")], alignment="spaceBetween"),
                        ft.Row([ft.Text("Saídas:"), ft.Text(f"R$ {t_sai:.2f}", color="red", weight="bold")], alignment="spaceBetween"),
                        ft.Row([ft.Text("Saldo Líquido:", weight="bold"), ft.Text(f"R$ {t_ent - t_sai:.2f}", weight="bold", size=16)], alignment="spaceBetween"),
                    ], spacing=5),
                    bgcolor=ft.Colors.BLUE_GREY_900, padding=15, border_radius=12
                )
                col_historico.controls.append(resumo_card)
            
            page.update()

        def abrir_edicao_extrato(mov):
            id_mov, d_obj, tipo, conta, desc, valor, cat = mov
            cor_tema = ft.Colors.GREEN_500 if tipo == 'ENTRADA' else ft.Colors.RED_500
            
            inp_data = ft.TextField(label="Data", value=d_obj.strftime('%d/%m/%Y'), width=320)
            inp_desc = ft.TextField(label="Descrição", value=desc, width=320)
            inp_valor = ft.TextField(label="Valor (R$)", value=f"{valor:.2f}", width=320)
            
            cats = banco.listar_categorias_por_tipo(tipo) or ["Geral"]
            drop_cat = ft.Dropdown(label="Categoria", width=320, options=[ft.dropdown.Option(c) for c in cats], value=cat if cat in cats else cats[0])
            
            bancos_list = banco.listar_contas_bancarias() or ["Dinheiro"]
            drop_conta = ft.Dropdown(label="Conta", width=320, options=[ft.dropdown.Option(b) for b in bancos_list], value=conta if conta in bancos_list else bancos_list[0])

            def salvar_edicao(e):
                e.control.disabled = True
                e.control.update()
                try:
                    novo_valor = float(inp_valor.value.replace(',', '.').strip())
                    nova_data_db = datetime.strptime(inp_data.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    nova_desc = inp_desc.value.strip()
                    
                    sucesso, msg = banco.atualizar_movimentacao(id_mov, nova_data_db, tipo, drop_conta.value, nova_desc, novo_valor, drop_cat.value)
                    
                    if sucesso:
                        bs_edit.open = False
                        atualizar_valores_globais()
                        show_snack("Lançamento atualizado com sucesso!")
                    else:
                        show_snack(msg, False)
                        e.control.disabled = False
                        e.control.update()
                except ValueError:
                    show_snack("Verifique os valores e a data.", False)
                    e.control.disabled = False
                    e.control.update()

            def perguntar_exclusao_extrato(e):
                def confirmar(e_conf):
                    e_conf.control.disabled = True
                    e_conf.control.update()
                    banco.deletar_movimentacao(id_mov)
                    dlg_conf.open = False
                    bs_edit.open = False
                    atualizar_valores_globais()
                    show_snack("Lançamento excluído com sucesso!")

                dlg_conf = ft.AlertDialog(
                    title=ft.Text("Excluir Lançamento"), 
                    content=ft.Text("Tem certeza que deseja apagar este registro?"), 
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_conf, 'open', False) or page.update()), 
                        ft.TextButton("Excluir", on_click=confirmar, style=ft.ButtonStyle(color=ft.Colors.RED))
                    ]
                )
                page.overlay.append(dlg_conf)
                dlg_conf.open = True
                page.update()

            btn_salvar = ft.Container(content=ft.Text("SALVAR", color=ft.Colors.WHITE, weight="bold"), bgcolor=cor_tema, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=salvar_edicao)
            btn_excluir = ft.Container(content=ft.Text("EXCLUIR REGISTRO", color=ft.Colors.WHITE, weight="bold"), bgcolor=ft.Colors.RED_700, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=perguntar_exclusao_extrato)
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text("Editar Lançamento", size=20, weight="bold"), 
                    inp_data, inp_desc, inp_valor, drop_cat, drop_conta, 
                    ft.Container(height=10), btn_salvar, ft.Container(height=5), btn_excluir, ft.Container(height=20)
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs_edit = ft.BottomSheet(bs_content)
            page.overlay.append(bs_edit)
            bs_edit.open = True
            page.update()

        tela_historico = ft.Column([
            ft.Text("Histórico (Últimos 30 dias)", size=24, weight="bold"),
            ft.Container(height=10),
            col_historico
        ], expand=True)

        # --- A PAGAR ---
        def abrir_edicao_boleto(conta_dados):
            id_c, desc_c, valor_c, venc_c, cat_c, rec_c, freq_c = conta_dados
            cor_tema = ft.Colors.ORANGE_500
            
            inp_desc = ft.TextField(label="Nome da Conta", value=desc_c, width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_valor = ft.TextField(label="Valor (R$)", value=f"{valor_c:.2f}", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_data = ft.TextField(label="Vencimento (DD/MM/AAAA)", value=venc_c.strftime('%d/%m/%Y') if not isinstance(venc_c, str) else venc_c, width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            
            cats = banco.listar_categorias_por_tipo('SAIDA') or ["Geral"]
            drop_cat = ft.Dropdown(label="Categoria", width=320, options=[ft.dropdown.Option(c) for c in cats], value=cat_c if cat_c in cats else cats[0], focused_border_color=cor_tema)
            
            switch_rec = ft.Switch(label="Repetir nos próximos meses?", value=rec_c, active_color=cor_tema)
            drop_freq = ft.Dropdown(label="Frequência", width=320, options=[ft.dropdown.Option("MENSAL"), ft.dropdown.Option("SEMANAL"), ft.dropdown.Option("ANUAL")], value=freq_c, focused_border_color=cor_tema)

            def salvar_edicao_boleto(e):
                e.control.disabled = True
                e.control.update()
                
                desc = inp_desc.value.strip()
                val_str = inp_valor.value.replace(',', '.').strip()
                
                if not desc or not val_str: 
                    e.control.disabled = False
                    e.control.update()
                    return

                try:
                    novo_valor = float(val_str)
                    data_db = datetime.strptime(inp_data.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    banco.atualizar_conta_pagar(id_c, desc, novo_valor, data_db, drop_cat.value, switch_rec.value, drop_freq.value)
                    bs_edit_bol.open = False
                    atualizar_valores_globais()
                    show_snack("Vencimento atualizado!")
                except ValueError:
                    show_snack("Verifique o valor ou a data", False)
                    e.control.disabled = False
                    e.control.update()

            def perguntar_exclusao_boleto(e):
                def confirmar(e_conf):
                    e_conf.control.disabled = True
                    e_conf.control.update()
                    banco.deletar_conta_pendente(id_c)
                    dlg_conf.open = False
                    bs_edit_bol.open = False
                    atualizar_valores_globais()
                    show_snack("Conta excluída com sucesso!")

                dlg_conf = ft.AlertDialog(
                    title=ft.Text("Excluir Conta"), 
                    content=ft.Text("Tem certeza que deseja apagar esta conta?"), 
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_conf, 'open', False) or page.update()), 
                        ft.TextButton("Excluir", on_click=confirmar, style=ft.ButtonStyle(color=ft.Colors.RED))
                    ]
                )
                page.overlay.append(dlg_conf)
                dlg_conf.open = True
                page.update()

            btn_salvar = ft.Container(content=ft.Text("SALVAR ALTERAÇÕES", color=ft.Colors.WHITE, weight="bold"), bgcolor=cor_tema, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=salvar_edicao_boleto)
            btn_excluir_bol = ft.Container(content=ft.Text("EXCLUIR CONTA", color=ft.Colors.WHITE, weight="bold"), bgcolor=ft.Colors.RED_700, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=perguntar_exclusao_boleto)
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text("Editar Vencimento", size=20, weight="bold", color=cor_tema), 
                    inp_desc, inp_valor, inp_data, drop_cat, switch_rec, drop_freq, 
                    ft.Container(height=10), btn_salvar, ft.Container(height=5), btn_excluir_bol, ft.Container(height=20)
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs_edit_bol = ft.BottomSheet(bs_content)
            page.overlay.append(bs_edit_bol)
            bs_edit_bol.open = True
            page.update()

        # --- A RECEBER ---
        def abrir_edicao_recebivel(conta_dados):
            id_c, desc_c, valor_c, venc_c, cat_c, rec_c, freq_c = conta_dados
            cor_tema = ft.Colors.TEAL_500
            
            inp_desc = ft.TextField(label="Descrição", value=desc_c, width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_valor = ft.TextField(label="Valor (R$)", value=f"{valor_c:.2f}", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_data = ft.TextField(label="Data Prevista (DD/MM/AAAA)", value=venc_c.strftime('%d/%m/%Y') if not isinstance(venc_c, str) else venc_c, width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            
            cats = banco.listar_categorias_por_tipo('ENTRADA') or ["Geral"]
            drop_cat = ft.Dropdown(label="Categoria", width=320, options=[ft.dropdown.Option(c) for c in cats], value=cat_c if cat_c in cats else cats[0], focused_border_color=cor_tema)
            
            switch_rec = ft.Switch(label="Repetir nos próximos meses?", value=rec_c, active_color=cor_tema)
            drop_freq = ft.Dropdown(label="Frequência", width=320, options=[ft.dropdown.Option("MENSAL"), ft.dropdown.Option("SEMANAL"), ft.dropdown.Option("ANUAL")], value=freq_c, focused_border_color=cor_tema)

            def salvar_edicao_recebivel(e):
                e.control.disabled = True
                e.control.update()
                
                desc = inp_desc.value.strip()
                val_str = inp_valor.value.replace(',', '.').strip()
                
                if not desc or not val_str: 
                    e.control.disabled = False
                    e.control.update()
                    return

                try:
                    novo_valor = float(val_str)
                    data_db = datetime.strptime(inp_data.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    banco.atualizar_conta_receber(id_c, desc, novo_valor, data_db, drop_cat.value, switch_rec.value, drop_freq.value)
                    bs_edit_rec.open = False
                    atualizar_valores_globais()
                    show_snack("Previsão atualizada!")
                except ValueError:
                    show_snack("Verifique o valor ou a data", False)
                    e.control.disabled = False
                    e.control.update()

            def perguntar_exclusao_recebivel(e):
                def confirmar(e_conf):
                    e_conf.control.disabled = True
                    e_conf.control.update()
                    banco.deletar_conta_receber_pendente(id_c)
                    dlg_conf.open = False
                    bs_edit_rec.open = False
                    atualizar_valores_globais()
                    show_snack("Previsão excluída!")

                dlg_conf = ft.AlertDialog(
                    title=ft.Text("Excluir Previsão"), 
                    content=ft.Text("Tem certeza que deseja apagar esta previsão?"), 
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_conf, 'open', False) or page.update()), 
                        ft.TextButton("Excluir", on_click=confirmar, style=ft.ButtonStyle(color=ft.Colors.RED))
                    ]
                )
                page.overlay.append(dlg_conf)
                dlg_conf.open = True
                page.update()

            btn_salvar = ft.Container(content=ft.Text("SALVAR ALTERAÇÕES", color=ft.Colors.WHITE, weight="bold"), bgcolor=cor_tema, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=salvar_edicao_recebivel)
            btn_excluir = ft.Container(content=ft.Text("EXCLUIR PREVISÃO", color=ft.Colors.WHITE, weight="bold"), bgcolor=ft.Colors.RED_700, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=perguntar_exclusao_recebivel)
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text("Editar Previsão", size=20, weight="bold", color=cor_tema), 
                    inp_desc, inp_valor, inp_data, drop_cat, switch_rec, drop_freq, 
                    ft.Container(height=10), btn_salvar, ft.Container(height=5), btn_excluir, ft.Container(height=20)
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs_edit_rec = ft.BottomSheet(bs_content)
            page.overlay.append(bs_edit_rec)
            bs_edit_rec.open = True
            page.update()

        def abrir_recebimento(id_c, nome, val):
            bancos_disp = banco.listar_contas_bancarias() or ["Dinheiro"]
            drop_conta_rec = ft.Dropdown(label="Receber em qual conta?", width=320, options=[ft.dropdown.Option(b) for b in bancos_disp], value=bancos_disp[0])
            inp_valor_rec = ft.TextField(label="Valor (Para Parcial, digite menos)", value=f"{val:.2f}", width=320, keyboard_type=ft.KeyboardType.NUMBER)
            inp_data_rec = ft.TextField(label="Data do Recebimento (DD/MM/AAAA)", value=datetime.today().strftime('%d/%m/%Y'), width=320)
            
            def confirmar_recebimento(e_rec):
                e_rec.control.disabled = True
                e_rec.control.update()
                try:
                    val_recebido = float(inp_valor_rec.value.replace(',', '.').strip())
                    data_pag_db = datetime.strptime(inp_data_rec.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    
                    sucesso, msg = banco.processar_recebimento_conta(id_c, drop_conta_rec.value, data_pag_db, val_recebido)
                    
                    if sucesso:
                        bs_rec.open = False
                        atualizar_valores_globais()
                        show_snack(msg, True)
                    else:
                        show_snack(msg, False)
                        e_rec.control.disabled = False
                        e_rec.control.update()
                except ValueError:
                    show_snack("Verifique o valor e a data!", False)
                    e_rec.control.disabled = False
                    e_rec.control.update()

            btn_conf_rec = ft.Container(content=ft.Text("CONFIRMAR RECEBIMENTO", color=ft.Colors.WHITE, weight="bold"), bgcolor=ft.Colors.TEAL_600, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=confirmar_recebimento)
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text(f"Receber: {nome}", size=20, weight="bold"), 
                    ft.Text(f"Falta receber: R$ {val:.2f}", size=14, color="gray"), 
                    inp_data_rec, inp_valor_rec, drop_conta_rec, 
                    ft.Container(height=10), btn_conf_rec
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs_rec = ft.BottomSheet(bs_content)
            page.overlay.append(bs_rec)
            bs_rec.open = True
            page.update()

        def atualizar_vencimentos():
            col_vencimentos.controls.clear()
            contas_pendentes = banco.listar_contas_pendentes()
            if contas_pendentes:
                for c in contas_pendentes[:4]: 
                    id_conta_pendente, nome_conta, valor_conta, data_venc, cat_conta, rec_conta, freq_conta = c

                    if isinstance(data_venc, str): 
                        data_venc = datetime.strptime(data_venc, '%Y-%m-%d').date()

                    item = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CALENDAR_MONTH, size=20, color="orange"),
                            ft.Column([
                                ft.Text(nome_conta, size=14, weight="bold"), 
                                ft.Text(f"Vence: {data_venc.strftime('%d/%m')}", size=12, color="gray")
                            ], spacing=2, expand=True),
                            ft.Text(f"R$ {valor_conta:.2f}", weight="bold"),
                            ft.Row([
                                ft.IconButton(ft.Icons.EDIT, icon_color="gray", tooltip="Editar Conta", on_click=lambda e, conta_dados=c: abrir_edicao_boleto(conta_dados)),
                                ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color="green", tooltip="Pagar Conta", on_click=lambda e, id_c=id_conta_pendente, n=nome_conta, v=valor_conta: mostrar_modal_pagamento(id_c, n, v))
                            ], spacing=0)
                        ]),
                        bgcolor=ft.Colors.BLUE_GREY_800, padding=10, border_radius=10
                    )
                    col_vencimentos.controls.append(item)
            else:
                col_vencimentos.controls.append(ft.Text("Nenhuma conta próxima em aberto 🎉", color="gray"))

        # ------------------------------------------
        # TELA 1: DASHBOARD (INÍCIO) E ACESSO RÁPIDO
        # ------------------------------------------
        card_saldo = ft.Container(
            content=ft.Column([
                ft.Text("SALDO DO MÊS", size=12, weight="bold", color=ft.Colors.GREY_400),
                txt_saldo_total, ft.Container(height=10),
                ft.Row([
                    ft.Column([ft.Text("Receitas", size=12, color=ft.Colors.GREY_400), txt_receitas], alignment=ft.MainAxisAlignment.START),
                    ft.Column([ft.Text("Despesas", size=12, color=ft.Colors.GREY_400), txt_despesas], alignment=ft.MainAxisAlignment.END),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ]),
            bgcolor=ft.Colors.BLUE_GREY_900, padding=20, border_radius=15, width=350
        )

        def abrir_lancamento(tipo_lancamento):
            cor_tema = ft.Colors.GREEN_500 if tipo_lancamento == "ENTRADA" else ft.Colors.RED_500
            titulo = "Nova Receita" if tipo_lancamento == "ENTRADA" else "Nova Despesa"

            inp_data = ft.TextField(label="Data (DD/MM/AAAA)", value=datetime.today().strftime('%d/%m/%Y'), width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_desc = ft.TextField(label="Descrição", width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_valor = ft.TextField(label="Valor (R$)", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor_tema, focused_border_color=cor_tema)
            
            categorias = banco.listar_categorias_por_tipo(tipo_lancamento) or ["Geral"]
            drop_cat = ft.Dropdown(label="Categoria", width=320, options=[ft.dropdown.Option(c) for c in categorias], value=categorias[0], focused_border_color=cor_tema)
            
            bancos_list = banco.listar_contas_bancarias() or ["Dinheiro"]
            drop_conta = ft.Dropdown(label="Conta", width=320, options=[ft.dropdown.Option(b) for b in bancos_list], value=bancos_list[0], focused_border_color=cor_tema)

            def salvar(e):
                e.control.disabled = True
                e.control.update()
                
                desc = inp_desc.value.strip()
                val_str = inp_valor.value.replace(',', '.').strip()
                if not desc or not val_str: 
                    e.control.disabled = False
                    e.control.update()
                    return

                try:
                    valor = float(val_str)
                    data_db = datetime.strptime(inp_data.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    sucesso, msg = banco.adicionar_movimentacao_avulsa(data_db, tipo_lancamento, drop_conta.value, desc, valor, drop_cat.value)
                    
                    if sucesso:
                        bs.open = False 
                        atualizar_valores_globais() 
                        show_snack("Lançamento salvo com sucesso!")
                    else:
                        show_snack(msg, False)
                        e.control.disabled = False
                        e.control.update()
                except ValueError:
                    show_snack("Verifique o valor ou a data", False)
                    e.control.disabled = False
                    e.control.update()

            btn_salvar = ft.Container(content=ft.Text("SALVAR LANÇAMENTO", color=ft.Colors.WHITE, weight="bold"), bgcolor=cor_tema, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=salvar)
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text(titulo, size=20, weight="bold", color=cor_tema), 
                    inp_data, inp_desc, inp_valor, drop_cat, drop_conta, 
                    ft.Container(height=10), btn_salvar, ft.Container(height=20)
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs = ft.BottomSheet(bs_content)
            page.overlay.append(bs)
            bs.open = True
            page.update()

        def abrir_lancamento_boleto(e):
            cor_tema = ft.Colors.ORANGE_500
            inp_desc = ft.TextField(label="Nome da Conta (Ex: Internet)", width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_valor = ft.TextField(label="Valor (R$)", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_data = ft.TextField(label="Vencimento (DD/MM/AAAA)", value=datetime.today().strftime('%d/%m/%Y'), width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            
            cats = banco.listar_categorias_por_tipo('SAIDA') or ["Geral"]
            drop_cat = ft.Dropdown(label="Categoria", width=320, options=[ft.dropdown.Option(c) for c in cats], value=cats[0], focused_border_color=cor_tema)
            
            switch_rec = ft.Switch(label="Repetir / Parcelar Lançamento?", value=False, active_color=cor_tema)
            drop_freq = ft.Dropdown(label="Frequência", width=320, options=[ft.dropdown.Option("MENSAL"), ft.dropdown.Option("SEMANAL"), ft.dropdown.Option("ANUAL")], value="MENSAL", focused_border_color=cor_tema, visible=False)
            inp_qtd = ft.TextField(label="Quantas vezes? (Vazio p/ infinito)", width=320, keyboard_type=ft.KeyboardType.NUMBER, focused_border_color=cor_tema, visible=False)

            def toggle_freq(e_tg):
                drop_freq.visible = switch_rec.value
                inp_qtd.visible = switch_rec.value
                page.update()
            
            switch_rec.on_change = toggle_freq

            def salvar_boleto(e_salvar):
                e_salvar.control.disabled = True
                e_salvar.control.update()
                
                desc = inp_desc.value.strip()
                val_str = inp_valor.value.replace(',', '.').strip()
                if not desc or not val_str: 
                    e_salvar.control.disabled = False
                    e_salvar.control.update()
                    return

                try:
                    valor = float(val_str)
                    venc_base = datetime.strptime(inp_data.value.strip(), '%d/%m/%Y')
                    
                    qtd_str = inp_qtd.value.strip()
                    recorrente = switch_rec.value
                    freq = drop_freq.value

                    if recorrente and qtd_str.isdigit():
                        qtd = int(qtd_str)
                        for i in range(qtd):
                            if freq == "MENSAL": 
                                nova_data = venc_base + relativedelta(months=i)
                            elif freq == "ANUAL": 
                                nova_data = venc_base + relativedelta(years=i)
                            elif freq == "SEMANAL": 
                                nova_data = venc_base + relativedelta(weeks=i)
                            else: 
                                nova_data = venc_base
                            
                            banco.adicionar_conta_pagar(f"{desc} ({i+1}/{qtd})", valor, nova_data.strftime('%Y-%m-%d'), drop_cat.value, False, freq)
                    else:
                        is_infinita = recorrente and not qtd_str
                        banco.adicionar_conta_pagar(desc, valor, venc_base.strftime('%Y-%m-%d'), drop_cat.value, is_infinita, freq)
                    
                    bs_bol.open = False 
                    atualizar_valores_globais() 
                    show_snack("Conta a pagar salva com sucesso!")
                except ValueError:
                    show_snack("Verifique o valor ou a data", False)
                    e_salvar.control.disabled = False
                    e_salvar.control.update()

            btn_salvar = ft.Container(content=ft.Text("SALVAR CONTA", color=ft.Colors.WHITE, weight="bold"), bgcolor=cor_tema, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=salvar_boleto)
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text("Novo Vencimento", size=20, weight="bold", color=cor_tema), 
                    inp_desc, inp_valor, inp_data, drop_cat, switch_rec, drop_freq, inp_qtd, 
                    ft.Container(height=10), btn_salvar, ft.Container(height=20)
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs_bol = ft.BottomSheet(bs_content)
            page.overlay.append(bs_bol)
            bs_bol.open = True
            page.update()

        def abrir_lancamento_recebivel(e):
            cor_tema = ft.Colors.TEAL_500
            inp_desc = ft.TextField(label="O que vai receber? (Ex: Aluguel)", width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_valor = ft.TextField(label="Valor (R$)", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_data = ft.TextField(label="Data Prevista (DD/MM/AAAA)", value=datetime.today().strftime('%d/%m/%Y'), width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            
            cats = banco.listar_categorias_por_tipo('ENTRADA') or ["Geral"]
            drop_cat = ft.Dropdown(label="Categoria", width=320, options=[ft.dropdown.Option(c) for c in cats], value=cats[0], focused_border_color=cor_tema)
            
            switch_rec = ft.Switch(label="Repetir / Parcelar Lançamento?", value=False, active_color=cor_tema)
            drop_freq = ft.Dropdown(label="Frequência", width=320, options=[ft.dropdown.Option("MENSAL"), ft.dropdown.Option("SEMANAL"), ft.dropdown.Option("ANUAL")], value="MENSAL", focused_border_color=cor_tema, visible=False)
            inp_qtd = ft.TextField(label="Quantas vezes? (Vazio p/ infinito)", width=320, keyboard_type=ft.KeyboardType.NUMBER, focused_border_color=cor_tema, visible=False)

            def toggle_freq(e_tg):
                drop_freq.visible = switch_rec.value
                inp_qtd.visible = switch_rec.value
                page.update()
            
            switch_rec.on_change = toggle_freq

            def salvar_recebivel(e_salvar):
                e_salvar.control.disabled = True
                e_salvar.control.update()
                
                desc = inp_desc.value.strip()
                val_str = inp_valor.value.replace(',', '.').strip()
                if not desc or not val_str: 
                    e_salvar.control.disabled = False
                    e_salvar.control.update()
                    return

                try:
                    valor = float(val_str)
                    venc_base = datetime.strptime(inp_data.value.strip(), '%d/%m/%Y')
                    
                    qtd_str = inp_qtd.value.strip()
                    recorrente = switch_rec.value
                    freq = drop_freq.value

                    if recorrente and qtd_str.isdigit():
                        qtd = int(qtd_str)
                        for i in range(qtd):
                            if freq == "MENSAL": 
                                nova_data = venc_base + relativedelta(months=i)
                            elif freq == "ANUAL": 
                                nova_data = venc_base + relativedelta(years=i)
                            elif freq == "SEMANAL": 
                                nova_data = venc_base + relativedelta(weeks=i)
                            else: 
                                nova_data = venc_base
                            
                            banco.adicionar_conta_receber(f"{desc} ({i+1}/{qtd})", valor, nova_data.strftime('%Y-%m-%d'), drop_cat.value, False, freq)
                    else:
                        is_infinita = recorrente and not qtd_str
                        banco.adicionar_conta_receber(desc, valor, venc_base.strftime('%Y-%m-%d'), drop_cat.value, is_infinita, freq)
                    
                    bs_rec_new.open = False 
                    atualizar_valores_globais() 
                    show_snack("Recebível salvo com sucesso!")
                except ValueError:
                    show_snack("Verifique o valor ou a data", False)
                    e_salvar.control.disabled = False
                    e_salvar.control.update()

            btn_salvar = ft.Container(content=ft.Text("SALVAR RECEBÍVEL", color=ft.Colors.WHITE, weight="bold"), bgcolor=cor_tema, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=salvar_recebivel)
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text("Nova Previsão", size=20, weight="bold", color=cor_tema), 
                    inp_desc, inp_valor, inp_data, drop_cat, switch_rec, drop_freq, inp_qtd, 
                    ft.Container(height=10), btn_salvar, ft.Container(height=20)
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs_rec_new = ft.BottomSheet(bs_content)
            page.overlay.append(bs_rec_new)
            bs_rec_new.open = True
            page.update()

        def abrir_lancamento_cartao(e):
            cartoes = banco.listar_cartoes()
            if not cartoes:
                show_snack("Cadastre um cartão na aba Gestão primeiro!", False)
                return

            cor_tema = ft.Colors.PURPLE_500
            
            mapa_cartoes = {c[1]: c for c in cartoes}
            opcoes_cartoes = [ft.dropdown.Option(c[1]) for c in cartoes]
            
            dp_cartao = ft.Dropdown(label="Cartão", width=320, options=opcoes_cartoes, value=cartoes[0][1], focused_border_color=cor_tema)
            inp_desc = ft.TextField(label="Descrição da Compra", width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_valor = ft.TextField(label="Valor (R$)", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_data = ft.TextField(label="Data (DD/MM/AAAA)", value=datetime.today().strftime('%d/%m/%Y'), width=320, cursor_color=cor_tema, focused_border_color=cor_tema)
            inp_parc = ft.TextField(label="Parcelas", value="1", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor_tema, focused_border_color=cor_tema)
            
            c_inicial = mapa_cartoes[dp_cartao.value]
            fat_calc_inicial = prever_fatura_alvo(datetime.today(), c_inicial[3], c_inicial[0])
            
            inp_fatura = ft.TextField(label="Fatura Alvo (MM/AAAA)", value=fat_calc_inicial.strftime('%m/%Y'), width=320, cursor_color=cor_tema, focused_border_color=cor_tema)

            def recalcular_fatura(e_args):
                texto_data = inp_data.value.strip()
                if len(texto_data) == 10:
                    try:
                        d_digitada = datetime.strptime(texto_data, '%d/%m/%Y')
                        c_selecionado = mapa_cartoes[dp_cartao.value]
                        nova_fat = prever_fatura_alvo(d_digitada, c_selecionado[3], c_selecionado[0])
                        inp_fatura.value = nova_fat.strftime('%m/%Y')
                        inp_fatura.update()
                    except ValueError:
                        pass
                        
            inp_data.on_change = recalcular_fatura
            dp_cartao.on_change = recalcular_fatura
            
            cats = banco.listar_categorias_por_tipo('SAIDA') or ["Geral"]
            drop_cat = ft.Dropdown(label="Categoria", width=320, options=[ft.dropdown.Option(c) for c in cats], value=cats[0], focused_border_color=cor_tema)

            def salvar(e_salvar):
                e_salvar.control.disabled = True
                e_salvar.control.update()
                
                try:
                    c_selecionado = mapa_cartoes[dp_cartao.value]
                    v = float(inp_valor.value.replace(',', '.').strip())
                    d = datetime.strptime(inp_data.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    p = int(inp_parc.value.strip())
                    m, a = inp_fatura.value.split('/')
                    
                    s, m_err = banco.adicionar_compra_cartao(
                        c_selecionado[0], inp_desc.value.strip(), v, d, p, drop_cat.value, m, a
                    )
                    
                    if s:
                        bs_cc.open = False
                        atualizar_valores_globais()
                        show_snack("Compra lançada com sucesso no cartão!")
                    else:
                        show_snack(m_err, False)
                        e_salvar.control.disabled = False
                        e_salvar.control.update()
                except Exception:
                    show_snack("Verifique os formatos de data e valores.", False)
                    e_salvar.control.disabled = False
                    e_salvar.control.update()

            btn_salvar = ft.Container(content=ft.Text("REGISTRAR COMPRA", color=ft.Colors.WHITE, weight="bold"), bgcolor=cor_tema, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=salvar)
            
            bs_content = ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                content=ft.Column([
                    ft.Text("Nova Compra no Cartão", size=20, weight="bold", color=cor_tema), 
                    dp_cartao, 
                    inp_desc, 
                    inp_valor, 
                    inp_data, 
                    inp_parc, 
                    drop_cat, 
                    inp_fatura, 
                    ft.Container(height=10), 
                    btn_salvar, 
                    ft.Container(height=20)
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
            )
            bs_cc = ft.BottomSheet(bs_content)
            page.overlay.append(bs_cc)
            bs_cc.open = True
            page.update()

        # --- BOTÕES DE ACESSO RÁPIDO (NOVO LAYOUT - 5 BOTÕES) ---
        btn_receita = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.ARROW_UPWARD, color=ft.Colors.WHITE, size=16), ft.Text("Receita", color=ft.Colors.WHITE, weight="bold", size=13)], alignment=ft.MainAxisAlignment.CENTER), 
            bgcolor=ft.Colors.GREEN_700, padding=10, border_radius=8, expand=True, ink=True, on_click=lambda e: abrir_lancamento("ENTRADA")
        )
        
        btn_despesa = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.ARROW_DOWNWARD, color=ft.Colors.WHITE, size=16), ft.Text("Despesa", color=ft.Colors.WHITE, weight="bold", size=13)], alignment=ft.MainAxisAlignment.CENTER), 
            bgcolor=ft.Colors.RED_700, padding=10, border_radius=8, expand=True, ink=True, on_click=lambda e: abrir_lancamento("SAIDA")
        )

        btn_pagar = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG, color=ft.Colors.WHITE, size=16), ft.Text("A Pagar", color=ft.Colors.WHITE, weight="bold", size=13)], alignment=ft.MainAxisAlignment.CENTER), 
            bgcolor=ft.Colors.ORANGE_700, padding=10, border_radius=8, expand=True, ink=True, on_click=abrir_lancamento_boleto
        )

        btn_recebivel = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.WHITE, size=16), ft.Text("A Receber", color=ft.Colors.WHITE, weight="bold", size=13)], alignment=ft.MainAxisAlignment.CENTER), 
            bgcolor=ft.Colors.TEAL_700, padding=10, border_radius=8, expand=True, ink=True, on_click=abrir_lancamento_recebivel
        )
        
        btn_compra_cartao = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.CREDIT_CARD, color=ft.Colors.WHITE, size=16), ft.Text("Compra no Cartão", color=ft.Colors.WHITE, weight="bold", size=13)], alignment=ft.MainAxisAlignment.CENTER), 
            bgcolor=ft.Colors.PURPLE_700, padding=10, border_radius=8, ink=True, on_click=abrir_lancamento_cartao, width=350
        )
        
        row_botoes = ft.Column([
            ft.Row([btn_receita, btn_despesa], spacing=10, width=350),
            ft.Row([btn_pagar, btn_recebivel], spacing=10, width=350),
            btn_compra_cartao
        ])

        tela_inicio = ft.Column([
            ft.Container(height=20),
            ft.Row([ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON)), ft.Text(f"Olá, {banco.USUARIO_NOME}!", size=22, weight="bold")]),
            ft.Container(height=20), 
            card_saldo, 
            ft.Container(height=30), 
            ft.Text("Acesso Rápido", size=16, weight="bold"), 
            row_botoes, 
            ft.Container(height=20), 
            ft.Text("Próximos Vencimentos", size=16, weight="bold"), 
            col_vencimentos
        ], scroll="auto", expand=True)

        # ------------------------------------------
        # TELA 3: ABA DE GESTÃO (LIMPA E SEGURA)
        # ------------------------------------------
        col_cartoes = ft.Column(scroll="auto", expand=True) 
        col_gestao_boletos = ft.Column(scroll="auto", expand=True)
        col_recebiveis = ft.Column(scroll="auto", expand=True)
        col_bancos = ft.Column(scroll="auto", expand=True)
        col_receitas_cats = ft.Column(scroll="auto", expand=True)
        col_despesas_cats = ft.Column(scroll="auto", expand=True)

        def abrir_dialogo_cartao(e):
            cores_disp = ["purple", "orange", "blue", "red", "green", "grey", "cyan", "amber", "pink"]
            cor_sel = ft.TextField(value="purple", visible=False)
            
            i_nm = ft.TextField(label="Nome do Cartão", width=320)
            i_lm = ft.TextField(label="Limite Total", keyboard_type=ft.KeyboardType.NUMBER, width=320)
            i_fc = ft.TextField(label="Dia Fechamento", keyboard_type=ft.KeyboardType.NUMBER, width=155)
            i_vc = ft.TextField(label="Dia Vencimento", keyboard_type=ft.KeyboardType.NUMBER, width=155)

            grade = ft.GridView(runs_count=5, max_extent=40, spacing=10, run_spacing=10, height=100)
            
            def sel_cor(nc): 
                cor_sel.value = nc
                for c in grade.controls:
                    c.border = ft.Border.all(2, "white") if c.bgcolor == nc else None
                page.update()
                
            for c in cores_disp: 
                grade.controls.append(ft.Container(bgcolor=c, border_radius=20, width=30, height=30, ink=True, on_click=lambda e, cor=c: sel_cor(cor)))
            
            sel_cor("purple")

            def salvar(e_s):
                e_s.control.disabled = True
                e_s.control.update()
                
                try:
                    if banco.adicionar_cartao(i_nm.value.strip(), i_lm.value.replace(',', '.'), i_fc.value, i_vc.value, cor_sel.value): 
                        dlg.open=False
                        atualizar_valores_globais()
                        show_snack("Cartão salvo com sucesso!")
                    else:
                        show_snack("Erro ao salvar", False)
                        e_s.control.disabled = False
                        e_s.control.update()
                except Exception: 
                    show_snack("Verifique os campos!", False)
                    e_s.control.disabled = False
                    e_s.control.update()
            
            dlg = ft.AlertDialog(
                title=ft.Text("Novo Cartão"), 
                content=ft.Column([
                    ft.Text("Nome do Cartão", color="gray", size=12), i_nm, 
                    ft.Text("Limite Total", color="gray", size=12), i_lm, 
                    ft.Row([
                        ft.Column([ft.Text("Fechamento", color="gray", size=12), i_fc]), 
                        ft.Column([ft.Text("Vencimento", color="gray", size=12), i_vc])
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                    ft.Text("Cor do Cartão:"), grade
                ], tight=True), 
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg, 'open', False) or page.update()), 
                    ft.TextButton("Salvar", on_click=salvar)
                ]
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        def abrir_edicao_cartao(c_dados):
            idc, nm, lm, fc, vc, cr = c_dados
            cor_sel = ft.TextField(value=cr, visible=False)
            
            i_nm = ft.TextField(label="Nome", value=nm, width=320)
            i_lm = ft.TextField(label="Limite", value=str(lm), keyboard_type=ft.KeyboardType.NUMBER, width=320)
            i_fc = ft.TextField(label="Fechamento", value=str(fc), keyboard_type=ft.KeyboardType.NUMBER, width=155)
            i_vc = ft.TextField(label="Vencimento", value=str(vc), keyboard_type=ft.KeyboardType.NUMBER, width=155)
            
            grade = ft.GridView(runs_count=5, max_extent=40, spacing=10, run_spacing=10, height=100)
            
            def sel_cor(nc): 
                cor_sel.value = nc
                for c in grade.controls:
                    c.border = ft.Border.all(2, "white") if c.bgcolor == nc else None
                page.update()
                
            for c in ["purple", "orange", "blue", "red", "green", "grey", "cyan", "amber", "pink"]: 
                grade.controls.append(ft.Container(bgcolor=c, border_radius=20, width=30, height=30, ink=True, on_click=lambda e, cor=c: sel_cor(cor)))
            
            sel_cor(cr)

            def salvar(e_s):
                e_s.control.disabled = True
                e_s.control.update()
                
                try:
                    if banco.atualizar_cartao(idc, i_nm.value.strip(), i_lm.value.replace(',', '.'), i_fc.value, i_vc.value, cor_sel.value): 
                        dlg.open=False
                        atualizar_valores_globais()
                        show_snack("Cartão atualizado!")
                    else:
                        show_snack("Erro ao salvar", False)
                        e_s.control.disabled = False
                        e_s.control.update()
                except Exception: 
                    show_snack("Erro ao salvar!", False)
                    e_s.control.disabled = False
                    e_s.control.update()

            def deletar(e_del):
                def conf(ec): 
                    ec.control.disabled = True
                    ec.control.update()
                    banco.deletar_cartao(idc)
                    d_c.open=False
                    dlg.open=False
                    atualizar_valores_globais()
                    show_snack("Cartão excluído!")
                    
                d_c = ft.AlertDialog(
                    title=ft.Text("Excluir"), 
                    content=ft.Text("Tem certeza que deseja apagar o cartão?"), 
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda _: setattr(d_c, 'open', False) or page.update()), 
                        ft.TextButton("Excluir", on_click=conf, style=ft.ButtonStyle(color=ft.Colors.RED))
                    ]
                )
                page.overlay.append(d_c)
                d_c.open = True
                page.update()
            
            dlg = ft.AlertDialog(
                title=ft.Text("Editar Cartão"), 
                content=ft.Column([
                    ft.Text("Nome do Cartão", color="gray", size=12), i_nm, 
                    ft.Text("Limite Total", color="gray", size=12), i_lm, 
                    ft.Row([
                        ft.Column([ft.Text("Fechamento", color="gray", size=12), i_fc]), 
                        ft.Column([ft.Text("Vencimento", color="gray", size=12), i_vc])
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                    ft.Text("Cor do Cartão:"), grade, 
                    ft.Row([
                        ft.Container(content=ft.Text("EXCLUIR", color="white"), bgcolor="red", width=120, height=40, alignment=ft.Alignment.CENTER, border_radius=8, ink=True, on_click=deletar), 
                        ft.Container(content=ft.Text("SALVAR", color="white"), bgcolor=cr, width=120, height=40, alignment=ft.Alignment.CENTER, border_radius=8, ink=True, on_click=salvar)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], tight=True)
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        def abrir_detalhes_cartao(dados):
            idc, nome, lim, df, dv, cor = dados
            fat_base = prever_fatura_alvo(datetime.today(), df, idc)
            mv = ft.TextField(value=fat_base.month, visible=False)
            av = ft.TextField(value=fat_base.year, visible=False)
            
            cfat = ft.Column(scroll="auto", height=300)
            tit = ft.Text(f"Fatura: {mv.value:02d}/{av.value}", weight="bold", size=18)
            tot = ft.Text("R$ 0.00", weight="bold", size=24, color=cor)
            rb = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            def abrir_edicao_compra(cmp):
                if cmp[5] != 'ABERTA': 
                    show_snack("Reabra a fatura para editar.", False)
                    return
                    
                i_d = ft.TextField(value=cmp[1], width=320, cursor_color=cor, focused_border_color=cor)
                i_v = ft.TextField(value=f"{cmp[2]:.2f}", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor, focused_border_color=cor)
                i_f = ft.TextField(value=f"{int(mv.value):02d}/{av.value}", width=320, cursor_color=cor, focused_border_color=cor)
                
                # ON_CHANGE para Edição
                def rc_ed(e):
                    texto = e.control.value.strip()
                    if len(texto) == 10:
                        try: 
                            nova = prever_fatura_alvo(datetime.strptime(texto, '%d/%m/%Y'), df, idc)
                            i_f.value = nova.strftime('%m/%Y')
                            i_f.update()
                        except ValueError: 
                            pass
                
                i_dt = ft.TextField(value=cmp[3].strftime('%d/%m/%Y'), width=320, cursor_color=cor, focused_border_color=cor, on_change=rc_ed)
                
                cats = banco.listar_categorias_por_tipo('SAIDA') or ["Geral"]
                dp_c = ft.Dropdown(width=320, options=[ft.dropdown.Option(c) for c in cats], value=cmp[4], focused_border_color=cor)

                def salvar(e):
                    e.control.disabled = True
                    e.control.update()
                    
                    try:
                        m, a = i_f.value.split('/')
                        s, m_err = banco.atualizar_compra_cartao(
                            cmp[0], i_d.value, float(i_v.value.replace(',','.')), 
                            datetime.strptime(i_dt.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d'), 
                            dp_c.value, m, a
                        )
                        if s: 
                            d_ec.open = False
                            carregar_compras_fatura()
                            atualizar_valores_globais()
                            show_snack("Atualizado com sucesso!")
                        else: 
                            show_snack(m_err, False)
                            e.control.disabled = False
                            e.control.update()
                    except Exception: 
                        show_snack("Erro de formato", False)
                        e.control.disabled = False
                        e.control.update()

                def deletar(e):
                    banco.deletar_compra_cartao(cmp[0])
                    d_ec.open = False
                    carregar_compras_fatura()
                    atualizar_valores_globais()
                    show_snack("Compra excluída!")

                d_ec = ft.AlertDialog(
                    title=ft.Text("Editar"), 
                    content=ft.Column([
                        ft.Text("Descrição", color="gray", size=12), i_d, 
                        ft.Text("Valor", color="gray", size=12), i_v, 
                        ft.Text("Data", color="gray", size=12), i_dt, 
                        ft.Text("Categoria", color="gray", size=12), dp_c, 
                        ft.Text("Fatura Alvo (MM/AAAA)", color="gray", size=12), i_f, 
                        ft.Row([
                            ft.Container(content=ft.Text("EXCLUIR", color="white"), bgcolor="red", width=120, height=40, alignment=ft.Alignment.CENTER, border_radius=8, ink=True, on_click=deletar), 
                            ft.Container(content=ft.Text("SALVAR", color="white"), bgcolor=cor, width=120, height=40, alignment=ft.Alignment.CENTER, border_radius=8, ink=True, on_click=salvar)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], tight=True)
                )
                page.overlay.append(d_ec)
                d_ec.open = True
                page.update()

            def carregar_compras_fatura():
                cfat.controls.clear()
                compras = banco.listar_compras_fatura(idc, int(mv.value), int(av.value))
                t = sum(c[2] for c in compras if c[5] in ['ABERTA', 'FECHADA']) if compras else 0.0
                ta = any(c[5] == 'ABERTA' for c in compras) if compras else False
                tf = any(c[5] == 'FECHADA' for c in compras) if compras else False
                tp = any(c[5] == 'PAGA' for c in compras) if compras else False

                if not compras: 
                    cfat.controls.append(ft.Text("Nenhuma compra.", color="gray"))
                else:
                    for cp in compras:
                        cor_t = "gray" if cp[5] in ['FECHADA', 'PAGA'] else "white"
                        icone = ft.Icons.LOCK if cp[5] in ['FECHADA', 'PAGA'] else ft.Icons.SHOPPING_BAG
                        
                        cfat.controls.append(
                            ft.ListTile(
                                leading=ft.Icon(icone, color=cor_t), 
                                title=ft.Text(cp[1], color=cor_t), 
                                subtitle=ft.Text(f"{cp[3].strftime('%d/%m')} • {cp[4]}", size=12, color="gray"), 
                                trailing=ft.Row([
                                    ft.Text(f"R$ {cp[2]:.2f}", weight="bold", color=cor_t), 
                                    ft.IconButton(ft.Icons.EDIT, icon_color="gray", visible=(cp[5]=='ABERTA'), on_click=lambda e, c_obj=cp: abrir_edicao_compra(c_obj))
                                ], tight=True, alignment=ft.MainAxisAlignment.END)
                            )
                        )

                tit.value = f"Fatura: {int(mv.value):02d}/{av.value}"
                tot.value = f"R$ {t:.2f}"
                
                rb.controls.clear()
                rb.controls.append(
                    ft.Container(content=ft.Text("+ Nova Compra", color="white", weight="bold"), bgcolor=cor, padding=10, border_radius=8, ink=True, on_click=abrir_nova_compra, expand=True, alignment=ft.Alignment.CENTER)
                )
                
                if ta: 
                    rb.controls.append(ft.Container(content=ft.Text("Fechar Fatura", color="white", weight="bold"), bgcolor="red", padding=10, border_radius=8, ink=True, on_click=fechar_fat, expand=True, alignment=ft.Alignment.CENTER))
                elif tf and not tp: 
                    rb.controls.append(ft.Container(content=ft.Text("Reabrir Fatura", color="white", weight="bold"), bgcolor="orange", padding=10, border_radius=8, ink=True, on_click=reabrir_fat, expand=True, alignment=ft.Alignment.CENTER))
                
                page.update()

            def nav(d):
                nx = datetime(int(av.value), int(mv.value), 1) + relativedelta(months=d)
                mv.value = nx.month
                av.value = nx.year
                carregar_compras_fatura()

            def abrir_nova_compra(e):
                h = datetime.today()
                fc = prever_fatura_alvo(h, df, idc)
                
                i_d = ft.TextField(width=320, cursor_color=cor, focused_border_color=cor)
                i_v = ft.TextField(width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor, focused_border_color=cor)
                i_p = ft.TextField(value="1", width=320, keyboard_type=ft.KeyboardType.NUMBER, cursor_color=cor, focused_border_color=cor)
                i_f = ft.TextField(value=fc.strftime('%m/%Y'), width=320, cursor_color=cor, focused_border_color=cor)
                
                # EVENTO ON_CHANGE
                def rc_nw(e):
                    texto = e.control.value.strip()
                    if len(texto) == 10:
                        try: 
                            nova = prever_fatura_alvo(datetime.strptime(texto, '%d/%m/%Y'), df, idc)
                            i_f.value = nova.strftime('%m/%Y')
                            i_f.update()
                        except ValueError: 
                            pass

                i_dt = ft.TextField(value=h.strftime('%d/%m/%Y'), width=320, cursor_color=cor, focused_border_color=cor, on_change=rc_nw)
                
                cats = banco.listar_categorias_por_tipo('SAIDA') or ["Geral"]
                dp_c = ft.Dropdown(width=320, options=[ft.dropdown.Option(c) for c in cats], value=cats[0], focused_border_color=cor)

                def salvar(e_s):
                    e_s.control.disabled = True
                    e_s.control.update()
                    
                    try:
                        m, a = i_f.value.split('/')
                        s, m_err = banco.adicionar_compra_cartao(
                            idc, i_d.value.strip(), float(i_v.value.replace(',','.')), 
                            datetime.strptime(i_dt.value.strip(), '%d/%m/%Y').strftime('%Y-%m-%d'), 
                            int(i_p.value.strip()), dp_c.value, m, a
                        )
                        if s: 
                            bs.open = False
                            carregar_compras_fatura()
                            atualizar_valores_globais()
                            show_snack("Salvo com sucesso!")
                        else: 
                            show_snack(m_err, False)
                            e_s.control.disabled = False
                            e_s.control.update()
                    except Exception: 
                        show_snack("Erro de formatação", False)
                        e_s.control.disabled = False
                        e_s.control.update()

                bs = ft.BottomSheet(
                    ft.Container(
                        padding=20, bgcolor=ft.Colors.BLUE_GREY_900, 
                        content=ft.Column([
                            ft.Text("Nova Compra", color=cor, size=20, weight="bold"), 
                            ft.Text("Descrição", color="gray", size=12), i_d, 
                            ft.Text("Valor", color="gray", size=12), i_v, 
                            ft.Text("Data", color="gray", size=12), i_dt, 
                            ft.Text("Parcelas", color="gray", size=12), i_p, 
                            ft.Text("Categoria", color="gray", size=12), dp_c, 
                            ft.Text("Fatura Alvo (MM/AAAA)", color="gray", size=12), i_f, 
                            ft.Container(content=ft.Text("REGISTRAR", color="white", weight="bold"), bgcolor=cor, width=320, height=50, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=salvar)
                        ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll="auto")
                    )
                )
                page.overlay.append(bs)
                bs.open = True
                page.update()

            def fechar_fat(e):
                def conf(ec):
                    ec.control.disabled = True
                    ec.control.update() 
                    d_c.open = False
                    s, m = banco.fechar_fatura_cartao(idc, int(mv.value), int(av.value))
                    carregar_compras_fatura()
                    atualizar_valores_globais()
                    show_snack(m, s)
                    
                d_c = ft.AlertDialog(
                    title=ft.Text("Atenção"), 
                    content=ft.Text("Enviar total para Contas a Pagar?"), 
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda _: setattr(d_c, 'open', False) or page.update()), 
                        ft.TextButton("Fechar", on_click=conf, style=ft.ButtonStyle(color=ft.Colors.GREEN))
                    ]
                )
                page.overlay.append(d_c)
                d_c.open = True
                page.update()

            def reabrir_fat(e): 
                e.control.disabled = True
                e.control.update()
                s, m = banco.reabrir_fatura_cartao(idc, int(mv.value), int(av.value))
                carregar_compras_fatura()
                atualizar_valores_globais()
                show_snack(m, s)

            dlg = ft.AlertDialog(
                content=ft.Container(
                    width=350, 
                    content=ft.Column([
                        ft.Text(nome, size=22, weight="bold", color=cor), 
                        ft.Row([
                            ft.IconButton(ft.Icons.ARROW_BACK_IOS, on_click=lambda e: nav(-1)), 
                            tit, 
                            ft.IconButton(ft.Icons.ARROW_FORWARD_IOS, on_click=lambda e: nav(1))
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                        ft.Container(content=ft.Column([ft.Text("Total", color="gray"), tot]), alignment=ft.Alignment.CENTER), 
                        ft.Divider(), 
                        cfat, 
                        rb
                    ], tight=True)
                )
            )
            page.overlay.append(dlg)
            dlg.open = True
            carregar_compras_fatura()

        def atualizar_listas_gestao():
            col_gestao_boletos.controls.clear()
            col_recebiveis.controls.clear()
            col_bancos.controls.clear()
            col_receitas_cats.controls.clear()
            col_despesas_cats.controls.clear()
            col_cartoes.controls.clear()

            # --- OTIMIZAÇÃO DE PERFORMANCE EXTREMA ---
            # Vai no banco uma única vez para pegar os limites consumidos
            sucesso, limites_bd = banco.executar_db("SELECT cartao_id, SUM(valor) FROM compras_cartao WHERE status IN ('ABERTA', 'FECHADA') GROUP BY cartao_id", fetchall=True)
            mapa_limites = {linha[0]: linha[1] for linha in limites_bd} if sucesso and limites_bd else {}
            # -----------------------------------------

            def perguntar_exclusao_gestao(e, tipo, nome_antigo):
                def confirmar(e_conf):
                    e_conf.control.disabled = True
                    e_conf.control.update()
                    
                    if tipo == 'BANCO': 
                        try:
                            banco.executar_db("DELETE FROM contas_bancarias WHERE nome = %s AND usuario_id = %s", (nome_antigo, banco.USUARIO_ID))
                            sucesso_db, msg_db = True, "Banco excluído com sucesso!"
                        except Exception as err:
                            sucesso_db, msg_db = False, f"Falha na exclusão: {err}"
                    else: 
                        sucesso_db, msg_db = banco.remover_categoria_segura(nome_antigo, tipo)
                    
                    dlg_conf.open = False
                    atualizar_valores_globais()
                    show_snack(msg_db, sucesso_db)
                    
                dlg_conf = ft.AlertDialog(
                    title=ft.Text("Excluir Item"), 
                    content=ft.Text(f"Apagar '{nome_antigo}'?"), 
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_conf, 'open', False) or page.update()), 
                        ft.TextButton("Excluir", on_click=confirmar, style=ft.ButtonStyle(color=ft.Colors.RED))
                    ]
                )
                page.overlay.append(dlg_conf)
                dlg_conf.open = True
                page.update()

            def abrir_edicao_gestao(e, tipo, nome_antigo):
                campo = ft.TextField(label="Novo Nome", value=nome_antigo)
                
                def salvar_edicao(e_salvar):
                    e_salvar.control.disabled = True
                    e_salvar.control.update()
                    novo = campo.value.strip()
                    if novo:
                        if tipo == 'BANCO': 
                            banco.executar_db("UPDATE contas_bancarias SET nome = %s WHERE nome = %s AND usuario_id = %s", (novo, nome_antigo, banco.USUARIO_ID))
                        else: 
                            banco.editar_categoria_inteligente(nome_antigo, novo, tipo)
                            
                    dlg_edicao.open = False
                    atualizar_valores_globais()

                def acionar_exclusao(e_excluir):
                    dlg_edicao.open = False
                    page.update()
                    perguntar_exclusao_gestao(e_excluir, tipo, nome_antigo)

                dlg_edicao = ft.AlertDialog(
                    title=ft.Text("Editar ou Excluir"), 
                    content=campo, 
                    actions=[
                        ft.TextButton("Excluir", on_click=acionar_exclusao, style=ft.ButtonStyle(color=ft.Colors.RED)),
                        ft.TextButton("Salvar", on_click=salvar_edicao)
                    ],
                    actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
                page.overlay.append(dlg_edicao)
                dlg_edicao.open = True
                page.update()

            def criar_item_gestao(nome, tipo, icone, cor):
                return ft.ListTile(
                    leading=ft.Icon(icone, color=cor), 
                    title=ft.Text(nome), 
                    trailing=ft.IconButton(ft.Icons.EDIT, icon_color="gray", tooltip="Editar", on_click=lambda e, t=tipo, n=nome: abrir_edicao_gestao(e, t, n))
                )

            # 1. Popula Cartões com Performance Otimizada
            for c in banco.listar_cartoes():
                fat_a = prever_fatura_alvo(datetime.today(), c[3], c[0])
                c_fat = banco.listar_compras_fatura(c[0], fat_a.month, fat_a.year)
                tot_fat = sum(x[2] for x in c_fat if x[5] == 'ABERTA') if c_fat else 0.0
                
                consumido = mapa_limites.get(c[0], 0.0)
                limite_disponivel = float(c[2]) - float(consumido)
                
                col_cartoes.controls.append(
                    ft.Container(
                        bgcolor=c[5], padding=15, border_radius=10, margin=ft.Margin.only(bottom=10), 
                        content=ft.Column([
                            ft.Row([
                                ft.Row([ft.Icon(ft.Icons.CREDIT_CARD, color="white"), ft.Text(c[1], weight="bold", color="white")]), 
                                ft.IconButton(ft.Icons.EDIT, icon_color="white", on_click=lambda e, cart=c: abrir_edicao_cartao(cart))
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                            ft.Row([
                                ft.Column([
                                    ft.Text(f"Fatura Atual: R$ {tot_fat:.2f}", weight="bold", color="white", size=14), 
                                    ft.Text(f"Lim. Disp: R$ {limite_disponivel:.2f} | Total: R$ {c[2]:.2f}", size=12, color="white70"),
                                    ft.Text(f"Fechamento: dia {c[3]} | Vencimento: dia {c[4]}", size=11, color="white70")
                                ], spacing=2, expand=True), 
                                ft.Container(
                                    content=ft.Text("Ver Fatura", color=c[5], weight="bold", size=12), 
                                    bgcolor="white", padding=5, border_radius=5, ink=True, 
                                    on_click=lambda e, cart=c: abrir_detalhes_cartao(cart)
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ])
                    )
                )

            # 2. Popula Contas a Pagar
            for c in banco.listar_contas_pendentes():
                id_conta, nome, valor, venc, cat, rec, freq = c
                if isinstance(venc, str): 
                    venc = datetime.strptime(venc, '%Y-%m-%d').date()
                
                col_gestao_boletos.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.RECEIPT_LONG, color=ft.Colors.ORANGE),
                        title=ft.Text(nome, weight="bold"),
                        subtitle=ft.Text(f"Vence: {venc.strftime('%d/%m/%Y')} • R$ {valor:.2f}", size=12, color="gray"),
                        trailing=ft.Row([
                            ft.IconButton(ft.Icons.EDIT, icon_color="gray", tooltip="Editar Conta", on_click=lambda e, dados=c: abrir_edicao_boleto(dados)),
                            ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color="green", tooltip="Pagar Conta", on_click=lambda e, id_c=id_conta, n=nome, v=valor: mostrar_modal_pagamento(id_c, n, v))
                        ], alignment=ft.MainAxisAlignment.END, tight=True)
                    )
                )

            # 3. Popula Recebíveis
            for rec in banco.listar_contas_receber_pendentes():
                id_r, n_rec, v_rec, d_rec, c_rec, r_rec, f_rec = rec
                if isinstance(d_rec, str): 
                    d_rec = datetime.strptime(d_rec, '%Y-%m-%d').date()
                
                col_recebiveis.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.TEAL),
                        title=ft.Text(n_rec, weight="bold"),
                        subtitle=ft.Text(f"Previsto: {d_rec.strftime('%d/%m/%Y')} • R$ {v_rec:.2f}", size=12, color="gray"),
                        trailing=ft.Row([
                            ft.IconButton(ft.Icons.EDIT, icon_color="gray", on_click=lambda e, dados=rec: abrir_edicao_recebivel(dados)),
                            ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color="teal", tooltip="Receber", on_click=lambda e, cid=id_r, n=n_rec, v=v_rec: abrir_recebimento(cid, n, v))
                        ], alignment=ft.MainAxisAlignment.END, tight=True)
                    )
                )

            # 4. Popula Bancos e Categorias (Visual Limpo)
            for b in banco.listar_contas_bancarias(): 
                col_bancos.controls.append(criar_item_gestao(b, 'BANCO', ft.Icons.ACCOUNT_BALANCE, ft.Colors.BLUE))
            for c in banco.listar_categorias_por_tipo('ENTRADA'): 
                col_receitas_cats.controls.append(criar_item_gestao(c, 'ENTRADA', ft.Icons.ARROW_UPWARD, ft.Colors.GREEN))
            for c in banco.listar_categorias_por_tipo('SAIDA'): 
                col_despesas_cats.controls.append(criar_item_gestao(c, 'SAIDA', ft.Icons.ARROW_DOWNWARD, ft.Colors.RED))
            
            page.update()

        def abrir_dialogo_novo(tipo):
            titulo = f"Novo(a) {'Banco' if tipo=='BANCO' else 'Categoria'}"
            campo = ft.TextField(label="Nome")
            
            def salvar_novo(e):
                val = campo.value.strip()
                if val:
                    if tipo == 'BANCO': 
                        banco.executar_db("INSERT INTO contas_bancarias (usuario_id, nome) VALUES (%s, %s)", (banco.USUARIO_ID, val))
                    else: 
                        banco.adicionar_categoria(val, tipo)
                        
                dlg_novo.open = False
                atualizar_valores_globais()
                
            dlg_novo = ft.AlertDialog(
                title=ft.Text(titulo), 
                content=campo, 
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_novo, 'open', False) or page.update()), 
                    ft.TextButton("Salvar", on_click=salvar_novo)
                ]
            )
            page.overlay.append(dlg_novo)
            dlg_novo.open = True
            page.update()

        btn_add_cartao = ft.Container(content=ft.Text("+ Adicionar Cartão", color="white", weight="bold"), bgcolor=ft.Colors.PURPLE_700, padding=10, border_radius=8, ink=True, on_click=abrir_dialogo_cartao, alignment=ft.Alignment.CENTER)
        btn_add_boleto = ft.Container(content=ft.Text("+ Nova Conta a Pagar", color="white", weight="bold"), bgcolor=ft.Colors.ORANGE_700, padding=10, border_radius=8, ink=True, on_click=abrir_lancamento_boleto, alignment=ft.Alignment.CENTER)
        btn_add_recebivel_aba = ft.Container(content=ft.Text("+ Nova Conta a Receber", color="white", weight="bold"), bgcolor=ft.Colors.TEAL_700, padding=10, border_radius=8, ink=True, on_click=abrir_lancamento_recebivel, alignment=ft.Alignment.CENTER)
        btn_add_banco = ft.Container(content=ft.Text("+ Adicionar Banco", color="white", weight="bold"), bgcolor=ft.Colors.BLUE_700, padding=10, border_radius=8, ink=True, on_click=lambda _: abrir_dialogo_novo('BANCO'), alignment=ft.Alignment.CENTER)
        btn_add_receita = ft.Container(content=ft.Text("+ Adicionar Receita", color="white", weight="bold"), bgcolor=ft.Colors.GREEN_700, padding=10, border_radius=8, ink=True, on_click=lambda _: abrir_dialogo_novo('ENTRADA'), alignment=ft.Alignment.CENTER)
        btn_add_despesa = ft.Container(content=ft.Text("+ Adicionar Despesa", color="white", weight="bold"), bgcolor=ft.Colors.RED_700, padding=10, border_radius=8, ink=True, on_click=lambda _: abrir_dialogo_novo('SAIDA'), alignment=ft.Alignment.CENTER)

        tela_gestao = ft.Tabs(
            length=6, selected_index=0,
            content=ft.Column([
                ft.TabBar(
                    scrollable=True,
                    tabs=[
                        ft.Tab(label="Cartões"), 
                        ft.Tab(label="A Pagar"), 
                        ft.Tab(label="A Receber"), 
                        ft.Tab(label="Bancos"), 
                        ft.Tab(label="Cat. Receitas"), 
                        ft.Tab(label="Cat. Despesas")
                    ]
                ),
                ft.TabBarView(
                    expand=True, 
                    controls=[
                        ft.Column([ft.Container(height=5), btn_add_cartao, col_cartoes], scroll="auto"),
                        ft.Column([ft.Container(height=5), btn_add_boleto, col_gestao_boletos], scroll="auto"),
                        ft.Column([ft.Container(height=5), btn_add_recebivel_aba, col_recebiveis], scroll="auto"),
                        ft.Column([ft.Container(height=5), btn_add_banco, col_bancos], scroll="auto"),
                        ft.Column([ft.Container(height=5), btn_add_receita, col_receitas_cats], scroll="auto"),
                        ft.Column([ft.Container(height=5), btn_add_despesa, col_despesas_cats], scroll="auto")
                    ]
                )
            ], expand=True)
        )

        # ------------------------------------------
        # ATUALIZAÇÃO GLOBAL E SEGURA
        # ------------------------------------------
        def atualizar_valores_globais():
            entradas, saidas = calcular_saldo_mes()
            saldo = entradas - saidas
            txt_saldo_total.value = f"R$ {saldo:.2f}"
            txt_saldo_total.color = ft.Colors.GREEN_400 if saldo >= 0 else ft.Colors.RED_400
            txt_receitas.value = f"R$ {entradas:.2f}"
            txt_despesas.value = f"R$ {saidas:.2f}"
            
            atualizar_historico() 
            atualizar_vencimentos()
            atualizar_listas_gestao() 
            page.update()

        # ------------------------------------------
        # TELA 4: ABA DE AJUSTES E EDITAR PERFIL
        # ------------------------------------------
        def abrir_editar_perfil(e):
            email_atual = banco.obter_email_usuario()
            
            inp_email = ft.TextField(label="E-mail", value=email_atual)
            inp_nova = ft.TextField(label="Nova Senha (deixe em branco para não alterar)", password=True, can_reveal_password=True)
            inp_conf = ft.TextField(label="Confirmar Nova Senha", password=True, can_reveal_password=True)
            
            def salvar_perfil(e_salv):
                e_salv.control.disabled = True
                e_salv.control.update()
                
                novo_email = inp_email.value.strip()
                senha = inp_nova.value
                confirma = inp_conf.value
                
                if not novo_email:
                    show_snack("O E-mail não pode ficar vazio!", False)
                    e_salv.control.disabled = False
                    e_salv.control.update()
                    return

                if senha or confirma:
                    if senha != confirma:
                        show_snack("As senhas não coincidem!", False)
                        e_salv.control.disabled = False
                        e_salv.control.update()
                        return
                    if len(senha) < 4:
                        show_snack("A senha deve ter pelo menos 4 caracteres.", False)
                        e_salv.control.disabled = False
                        e_salv.control.update()
                        return
                    
                    sucesso, msg = banco.atualizar_perfil(novo_email, senha)
                else:
                    sucesso, msg = banco.atualizar_perfil(novo_email)

                if sucesso:
                    dlg_perfil.open = False
                    show_snack("Perfil atualizado com sucesso!")
                else:
                    show_snack("Erro ao atualizar o perfil.", False)
                    e_salv.control.disabled = False
                    e_salv.control.update()
            
            dlg_perfil = ft.AlertDialog(
                title=ft.Text("Editar Perfil"), 
                content=ft.Column([inp_email, inp_nova, inp_conf], tight=True), 
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_perfil, 'open', False) or page.update()), 
                    ft.TextButton("Salvar", on_click=salvar_perfil)
                ]
            )
            page.overlay.append(dlg_perfil)
            dlg_perfil.open = True
            page.update()

        async def sair_da_conta(e):
            await ft.SharedPreferences().remove("login_user")
            await ft.SharedPreferences().remove("login_pass")
            page.clean()
            await renderizar_login()

        def alterar_tema(e):
            page.theme_mode = ft.ThemeMode.DARK if e.control.value else ft.ThemeMode.LIGHT
            page.update()

        switch_tema = ft.Switch(label="Modo Escuro", value=True, on_change=alterar_tema)

        btn_editar_perfil = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.MANAGE_ACCOUNTS, color="white"), ft.Text("Editar Perfil", color="white", weight="bold")], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.BLUE_700, padding=10, border_radius=8, ink=True, on_click=abrir_editar_perfil, width=180
        )

        tela_config = ft.Column([
            ft.Text("Meu Perfil", size=24, weight="bold"),
            ft.Container(height=10),
            ft.ListTile(leading=ft.Icon(ft.Icons.PERSON), title=ft.Text("Logado como"), subtitle=ft.Text(banco.USUARIO_NOME)),
            ft.Row([ft.Container(width=15), btn_editar_perfil]),
            switch_tema, 
            ft.Divider(height=20, color="transparent"),
            ft.Text("Informações do Sistema", size=16, weight="bold", color="gray"),
            ft.ListTile(leading=ft.Icon(ft.Icons.CODE, color="blue"), title=ft.Text("Desenvolvedor"), subtitle=ft.Text("Thiago Oliveira")),
            ft.ListTile(leading=ft.Icon(ft.Icons.SUPPORT_AGENT, color="green"), title=ft.Text("Suporte via WhatsApp"), subtitle=ft.Text("(00) 00000-0000")),
            ft.Container(height=20),
            ft.Container(content=ft.Text("SAIR DA CONTA", color="white", weight="bold"), bgcolor="red", padding=15, border_radius=8, alignment=ft.Alignment.CENTER, ink=True, on_click=sair_da_conta)
        ], scroll="auto", expand=True)

        # ------------------------------------------
        # MENU DE NAVEGAÇÃO INFERIOR
        # ------------------------------------------
        def mudar_aba(e):
            area_conteudo.content = [tela_inicio, tela_historico, tela_gestao, tela_config][e.control.selected_index]
            page.update()

        page.navigation_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Início"),
                ft.NavigationBarDestination(icon=ft.Icons.RECEIPT_LONG, label="Histórico"),
                ft.NavigationBarDestination(icon=ft.Icons.CATEGORY, label="Gestão"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Ajustes")
            ], on_change=mudar_aba
        )
        
        page.add(area_conteudo)
        mudar_aba(type('obj', (object,), {'control': type('obj', (object,), {'selected_index': 0})}))
        
        atualizar_valores_globais()
        verificar_lembretes_vencimento()


    # ==========================================
    # TELA DE LOGIN E REGISTRO SEGURA
    # ==========================================
    txt_usuario = ft.TextField(label="Usuário", width=300, prefix_icon=ft.Icons.PERSON)
    txt_senha = ft.TextField(label="Senha", width=300, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
    chk_lembrar = ft.Checkbox(label="Lembrar meu acesso", value=False)

    async def tentar_login(e=None):
        if e:
            e.control.disabled = True
            e.control.update()
            
        u = txt_usuario.value
        p = txt_senha.value
        sucesso, msg = banco.login_sistema(u, p)
        
        if sucesso:
            if chk_lembrar.value:
                await ft.SharedPreferences().set("login_user", u)
                await ft.SharedPreferences().set("login_pass", p)
            else:
                await ft.SharedPreferences().remove("login_user")
                await ft.SharedPreferences().remove("login_pass")
                
            page.clean()
            page.horizontal_alignment = ft.CrossAxisAlignment.START
            page.vertical_alignment = ft.MainAxisAlignment.START
            construir_app_principal() 
        else:
            show_snack(msg, False)
            if e:
                e.control.disabled = False
                e.control.update()
    
    def abrir_registro(e):
        inp_nome = ft.TextField(label="Nome Completo")
        inp_email = ft.TextField(label="E-mail")
        inp_usr = ft.TextField(label="Usuário (Login)")
        inp_pwd = ft.TextField(label="Senha", password=True, can_reveal_password=True)
        
        def salvar_registro(e_reg):
            if not all([inp_nome.value, inp_email.value, inp_usr.value, inp_pwd.value]): 
                return
                
            e_reg.control.disabled = True
            e_reg.control.update()
            
            suc, msg = banco.registrar_novo_usuario(inp_nome.value, inp_email.value, inp_usr.value, inp_pwd.value)
            
            if suc:
                dlg_reg.open = False
                show_snack(msg, suc)
            else:
                show_snack(msg, False)
                e_reg.control.disabled = False
                e_reg.control.update()

        dlg_reg = ft.AlertDialog(
            title=ft.Text("Criar Conta"), 
            content=ft.Column([inp_nome, inp_email, inp_usr, inp_pwd], tight=True), 
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_reg, 'open', False) or page.update()), 
                ft.TextButton("Registrar", on_click=salvar_registro)
            ]
        )
        page.overlay.append(dlg_reg)
        dlg_reg.open = True
        page.update()

    def abrir_recuperacao(e):
        inp_email = ft.TextField(label="Digite seu E-mail cadastrado")
        
        def enviar_recuperacao(e_rec):
            if not inp_email.value: 
                return
                
            e_rec.control.disabled = True
            e_rec.control.update()
            
            suc, msg = banco.redefinir_senha_por_email(inp_email.value)
            dlg_rec.open = False
            
            if suc:
                page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="green", duration=7000)
            else:
                page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="red", duration=7000)
            
            page.snack_bar.open = True
            page.update()

        dlg_rec = ft.AlertDialog(
            title=ft.Text("Recuperar Senha"), 
            content=inp_email, 
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_rec, 'open', False) or page.update()), 
                ft.TextButton("Recuperar", on_click=enviar_recuperacao)
            ]
        )
        page.overlay.append(dlg_rec)
        dlg_rec.open = True
        page.update()

    btn_entrar = ft.Container(
        content=ft.Text("ENTRAR", color=ft.Colors.WHITE, weight="bold", size=16), 
        width=300, height=50, bgcolor=ft.Colors.BLUE_700, border_radius=8, 
        alignment=ft.Alignment.CENTER, ink=True, on_click=tentar_login
    )
    
    row_opcoes = ft.Row([
        ft.TextButton("Criar nova conta", on_click=abrir_registro), 
        ft.TextButton("Esqueci minha senha", on_click=abrir_recuperacao)
    ], width=300, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    async def renderizar_login():
        user_salvo = await ft.SharedPreferences().get("login_user")
        pass_salva = await ft.SharedPreferences().get("login_pass")
        
        if user_salvo and pass_salva:
            sucesso, msg = banco.login_sistema(user_salvo, pass_salva)
            if sucesso:
                txt_usuario.value = user_salvo
                txt_senha.value = pass_salva
                chk_lembrar.value = True
                page.clean()
                page.horizontal_alignment = ft.CrossAxisAlignment.START
                page.vertical_alignment = ft.MainAxisAlignment.START
                construir_app_principal()
                return

        page.clean()
        page.navigation_bar = None 
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        
        txt_usuario.value = user_salvo if user_salvo else ""
        txt_senha.value = pass_salva if pass_salva else ""
        chk_lembrar.value = True if (user_salvo and pass_salva) else False

        page.add(
            ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=80, color=ft.Colors.BLUE_400),
            ft.Text("MEU GESTOR", size=28, weight="bold"),
            ft.Text("Acesso Restrito", size=14, color=ft.Colors.GREY_400),
            ft.Container(height=30), 
            txt_usuario, 
            txt_senha, 
            ft.Container(content=chk_lembrar, width=300),
            ft.Container(height=10), 
            btn_entrar, 
            row_opcoes
        )
        page.update()

    await renderizar_login()

ft.run(main)
