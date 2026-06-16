-- Outcome statuses with human-readable descriptions.
select *
from (
    values
        ('exit', 'Successful sale/exit at end of horizon'),
        ('refi_fail', 'Refinancing gate not cleared at Month ~19'),
        ('default', 'Insolvency before refinancing'),
        ('survived_no_exit', 'Solvent at horizon but no exit transaction')
) as t(status, description)
