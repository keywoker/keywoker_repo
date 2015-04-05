# -*- encoding: utf-8 -*-

import base64

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools

import logging

# _logger = logging.getLogger(__name__)

class account_rus_import(osv.osv_memory):
    _name = 'account.rus.import'
    _description = 'Import Russian statements file'
    _columns = {
        'file_data': fields.binary('Import statements File', required=True),
        'file_fname': fields.char('Import statements Filename', size=128, required=True),
        'note': fields.text('Log'),
        'temporary_account_id': fields.many2one('account.account', 'Temporary Account', help="It acts as a temporary account for general amount", required=True),  # domain="[('type','!=','view')]"
    }

    def _get_default_tmp_account(self, cr, uid, context):
        tmp_accounts = self.pool.get('account.account').search(cr, uid, [('code', '=', '490000')])
        if tmp_accounts and len(tmp_accounts) > 0:
            tmp_account_id = tmp_accounts[0]
        else:
            tmp_account_id = False
        return tmp_account_id

    _defaults = {
        'file_fname': lambda *a: '',
        'temporary_account_id': _get_default_tmp_account,
    }

    def file_parsing(self, cr, uid, ids, context=None, batch=False, rfile=None, rfilename=None):

        def acc_number_parsing(obj, line_number):
            acc_res = {}
            acc_res_number = ''
            while rmspaces(obj[line_number][0]) != u'КонецРасчСчет':  # !!! Документ
                if obj[line_number][0] == u'ДатаНачала':
                    acc_res['begin_date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT,
                                                          time.strptime(rmspaces(obj[line_number][1]), '%d.%m.%Y'))
                elif obj[line_number][0] == u'ДатаКонца':
                    acc_res['end_date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT,
                                                        time.strptime(rmspaces(obj[line_number][1]), '%d.%m.%Y'))
                elif obj[line_number][0] == u'РасчСчет':
                    acc_res_number = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'НачальныйОстаток':
                    acc_res['balance_start'] = float(rmspaces(obj[line_number][1]))
                elif obj[line_number][0] == u'ВсегоПоступило':
                    acc_res['balance_plus'] = float(rmspaces(obj[line_number][1]))
                elif obj[line_number][0] == u'ВсегоСписано':
                    acc_res['balance_minus'] = float(rmspaces(obj[line_number][1]))
                elif obj[line_number][0] == u'КонечныйОстаток':
                    acc_res['balance_end'] = float(rmspaces(obj[line_number][1]))
                line_number += 1
            line_number += 1
            return acc_res_number, acc_res, line_number

        if context is None:
            context = {}
        if batch:
            rfile = str(rfile)
            rfilename = rfilename
        else:
            data = self.browse(cr, uid, ids)[0]
            try:
                rfile = data.file_data
                rfilename = data.file_fname
                temporaryaccount = data.temporary_account_id.id
            except:
                raise osv.except_osv(_('Error'), _('Wizard in incorrect state. Please hit the Cancel button'))
                # return {}
        recordlist = unicode(base64.decodestring(rfile), 'windows-1251', 'strict').split('\n')
        strobj = []
        for line in recordlist:
            strobj.append(line.split('='))

        format_import_file = ''
        encoding_file = ''
        statements = {}
        note = []
        inc_desc = 1
        if rmspaces(recordlist[0]) != '1CClientBankExchange':
            raise osv.except_osv(_('Error'), _('Incorrect description of import file'))

        if strobj[inc_desc][0] == u'ВерсияФормата':
            format_import_file = rmspaces(strobj[inc_desc][1])
            note.append(recordlist[inc_desc] + '\n')
            inc_desc += 1
        else:
            raise osv.except_osv(_('Error'), _('Incorrect description of import file'))

        if strobj[inc_desc][0] == u'Кодировка':
            encoding_file = rmspaces(strobj[inc_desc][1])
            note.append(recordlist[inc_desc] + '\n')
            inc_desc += 1
        else:
            raise osv.except_osv(_('Error'), _('Incorrect description of import file'))

        if strobj[inc_desc][0] == u'Отправитель':
            note.append(recordlist[inc_desc] + '\n')
            inc_desc += 1
        if strobj[inc_desc][0] == u'Получатель':
            note.append(recordlist[inc_desc] + '\n')
            inc_desc += 1
        else:
            raise osv.except_osv(_('Error'), _('Incorrect description of import file'))
        
        if strobj[inc_desc][0] == u'ДатаСоздания':
            note.append(recordlist[inc_desc] + '\n')
            inc_desc += 1
        if strobj[inc_desc][0] == u'ВремяСоздания':
            note.append(recordlist[inc_desc] + '\n')
            inc_desc += 1

        if strobj[inc_desc][0] == u'ДатаНачала':
            note.append(recordlist[inc_desc] + '\n')
            statements['begin_date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT,
                                                     time.strptime(rmspaces(strobj[inc_desc][1]), '%d.%m.%Y'))
            tmp_acc, tmp_acc_res, slide_i = acc_number_parsing(strobj, inc_desc)
            inc_desc += 1
        else:
            raise osv.except_osv(_('Error'), _('Incorrect description of import file'))
        if strobj[inc_desc][0] == u'ДатаКонца':
            note.append(recordlist[inc_desc] + '\n')
            statements['end_date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT,
                                                   time.strptime(rmspaces(strobj[inc_desc][1]), '%d.%m.%Y'))
            inc_desc += 1
        else:
            raise osv.except_osv(_('Error'), _('Incorrect description of import file'))
        acc_numbers = []
        while strobj[inc_desc][0] == u'РасчСчет':
            acc_number = {}
            acc_number['detail'] = []
            acc_number['statement_line'] = []
            acc_number['acc_number'] = rmspaces(strobj[inc_desc][1])
            acc_number['journal_id'] = False
            acc_number['bank_account'] = False
            bank_ids = self.pool.get('res.partner.bank').search(cr, uid,
                                                                [('acc_number', '=', acc_number['acc_number'])])
            if bank_ids and len(bank_ids) > 0:
                bank_accs = self.pool.get('res.partner.bank').browse(cr, uid, bank_ids)
                for bank_acc in bank_accs:
                    if bank_acc.journal_id.id:
                        acc_number['journal_id'] = bank_acc.journal_id
                        acc_number['bank_account'] = bank_acc
                        break
            if not acc_number['bank_account']:
                raise osv.except_osv(_('Error'), _("No matching Bank Account (with Account Journal) found.\n\n"
                                                   "Please set-up a Bank Account with as Account Number '%s' "
                                                   "and an Account Journal.") % (acc_number['acc_number']))
            acc_numbers.append(acc_number)
            inc_desc += 1

        def statement_line_parsing(obj, line_number):
            statementLine = {}
            statementLine['note'] = []
            while rmspaces(obj[line_number][0]) != u'КонецДокумента':
                if obj[line_number][0] == u'Номер':
                    statementLine['ref'] = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'Дата':
                    statementLine['date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(obj[line_number][1]),'%d.%m.%Y'))
                elif obj[line_number][0] == u'Сумма':
                    statementLine['amount'] = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'ПлательщикСчет':
                    statementLine['payer_acc'] = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'Плательщик':
                    statementLine['payer'] = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'ПлательщикИНН':
                    statementLine['payer_inn'] = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'ПолучательСчет':
                    statementLine['recipient_acc'] = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'Получатель':
                    statementLine['recipient'] = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'ПолучательИНН':
                    statementLine['recipient_inn'] = rmspaces(obj[line_number][1])
                elif obj[line_number][0] == u'НазначениеПлатежа':
                    statementLine['name'] = rmspaces(obj[line_number][1])
                else:
                    statementLine['note'].append(obj[line_number][0] + ': ' + obj[line_number][1])
                line_number += 1
            line_number += 1
            return statementLine, line_number

        #for i in range(inc_desc,len(strobj)-1):
        i = inc_desc
        while rmspaces(strobj[i][0]) != u'КонецФайла':
            # _logger = logging.getLogger(__name__)
            # _logger.info('ENDFILE %s %s %s', i, len(strobj)-1, strobj[i][0])
            if strobj[i][0] == u'СекцияРасчСчет':  # Документ
                # _logger = logging.getLogger(__name__)
                # _logger.info('SEC RASH')
                for acc_one in acc_numbers:
                    if acc_one['acc_number'] == tmp_acc:
                        acc_one['detail'].append(tmp_acc_res)
                        break

            elif strobj[i][0] == u'СекцияДокумент':
                tmp_statementLine, slide_i = statement_line_parsing(strobj, i)
                # _logger = logging.getLogger(__name__)
                # _logger.info('SEC DOC')
                for acc_one in acc_numbers:
                    if acc_one['acc_number'] == tmp_statementLine['payer_acc'] or \
                                    acc_one['acc_number'] == tmp_statementLine['recipient_acc']:
                        tmp_statementLine['sequence'] = len(acc_one['statement_line']) + 1
                        acc_one['statement_line'].append(tmp_statementLine)
                        break
            if i < (len(strobj)-2):
                i += 1

        for slide_i, statement in enumerate(acc_numbers):
            period_id = self.pool.get('account.period').search(cr, uid,
                                                        [('company_id', '=', statement['journal_id'].company_id.id),
                                                        ('date_start', '<=', statements['end_date']),
                                                        ('date_stop', '>=', statements['end_date'])])
            if not period_id and len(period_id) == 0:
                raise osv.except_osv(_('Error'), _("The Statement New Balance date doesn't fall within a defined Accounting Period! Please create the Accounting Period for date %s for the company %s.") % (statements['end_date'], statement['journal_id'].company_id.name))
            statement['period_id'] = period_id[0]

            statement['note'] = note
            cr.execute('SELECT balance_end_real \
            FROM account_bank_statement \
            WHERE journal_id = %s and date <= %s \
            ORDER BY date DESC,id DESC LIMIT 1', (statement['journal_id'].id, statements['begin_date']))
            res = cr.fetchone()
            balance_start_check = res and res[0]
            if balance_start_check == None:
                if statement['journal_id'].default_debit_account_id and (statement['journal_id'].default_credit_account_id == statement['journal_id'].default_debit_account_id):
                    balance_start_check = statement['journal_id'].default_debit_account_id.balance
                else:
                    raise osv.except_osv(_('Error'), _("Configuration Error in journal %s!\nPlease verify the Default Debit and Credit Account settings.") % statement['journal_id'].name)
            if balance_start_check != tmp_acc_res['balance_start']:  # statement['balance_start']
                statement['note'].append(_("The Statement %s Starting Balance (%.2f) does not correspond with the previous Closing Balance (%.2f) in journal %s!") % (statement['acc_number'] + ' #' + statements['begin_date'] + ':' + statements['end_date'], tmp_acc_res['balance_start'], balance_start_check, statement['journal_id'].name))
            if not(statement.get('period_id')):
                raise osv.except_osv(_('Error'), _(' No transactions or no period in file !'))
            data = {
                'name': statement['acc_number'] + ' #' + statements['begin_date'] + ':' + statements['end_date'],
                'date': datetime.now(),
                'journal_id': statement['journal_id'].id,
                'period_id': statement['period_id'],
                'balance_start': tmp_acc_res['balance_start'],   # 'balance_start': statement['balance_start'],
                'balance_end_real': tmp_acc_res['balance_end'],
            }
            statement['id'] = self.pool.get('account.bank.statement').create(cr, uid, data, context=context)
            for line in statement['statement_line']:
                partner = None
                partner_id = None
                invoice = False
                if line['payer_acc'] == statement['acc_number']:
                    pass
                else:
                    ids = self.pool.get('res.partner.bank').search(cr, uid, [('acc_number', '=', str(line['payer_acc']))])
                    _logger = logging.getLogger(__name__)
                    _logger.info('IDS %s', ids)
                    p_id = None

                    if ids and len(ids) > 0:
                        partner = self.pool.get('res.partner.bank').browse(cr, uid, ids[0], context=context)
                        _logger = logging.getLogger(__name__)
                        _logger.info('PARTNER %s', partner)
                        p_id = partner.partner_id.id
                        line['account'] = partner.partner_id.property_account_receivable.id
                        ids = ids[0]
                    else:
                        _logger = logging.getLogger(__name__)
                        _logger.info('PARTNER_NO %s', ids)
                        ids = ''
                    if not partner and not invoice:
                        line['account'] = temporaryaccount
                        line['name'] = line['name'] + '\n' + line['payer_inn']
                    data = {
                        'name': line['name'],
                        'note': '\n'.join(line['note']),
                        'date': line['date'],
                        'amount': line['amount'],
                        'partner_id': p_id,
                        #'account_id': line['account'], #Looks like reconsilation will not work with it
                        'statement_id': statement['id'],
                        'ref': line['ref'],
                        'sequence': line['sequence'],
                        'bank_account_id': ids,
                    }
                    data_check = {
                        'date': line['date'],
                        'amount': line['amount'],
                        'ref': line['ref'],
                        'account_id': line['account'],
                    }
                    ids_line_statement = self.pool.get('account.bank.statement.line').search(cr, uid,
                                                                                [('date', '=', data_check['date']),
                                                                                ('amount', '=', data_check['amount']),
                                                                                ('ref', '=', data_check['ref']),
                                                                                #('account_id', '=', data_check['account_id'])
                                                                                ])
                    if ids_line_statement:
                        statement['note'].append(_('Statement line %s from %s alredy exist.') %
                                                (data_check['ref'], data_check['date']))
                    else:
                        self.pool.get('account.bank.statement.line').create(cr, uid, data, context=context)
                    
                if statement['note']:
                    self.pool.get('account.bank.statement').write(cr, uid, [statement['id']],
                                                              {'rusimport_note': '\n'.join(statement['note'])},
                                                              context=context)
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                               'account', 'action_bank_statement_tree')
        action = self.pool[model].browse(cr, uid, action_id, context=context)
        return {
            'name': action.name,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'res_model': action.res_model,
            'domain': action.domain,
            'context': action.context,
            'type': 'ir.actions.act_window',
            'search_view_id': action.search_view_id.id,
            'views': [(v.view_id.id, v.view_mode) for v in action.view_ids]
        }



def rmspaces(s):
    return " ".join(s.split())