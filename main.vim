if !has('python3')
	echo "Error: required vim copiled with +python3"
	finish
endif

let g:vim_yo_path = expand('<sfile>:p:h')
let g:vim_yo_dict = vim_yo_path . "/" . "yo"

python3 << EOF
import sys, vim
sys.path.append(vim.eval("g:vim_yo_path"))
EOF

function! g:CorrectYo()
python3 << EOF
import spellchecker
spellchecker.main()
EOF

endfunction
nnoremap <Leader> :call g:CorrectYo() <CR>

" Аблезгов, еще еж.
" аблезгова Автомассажер.
