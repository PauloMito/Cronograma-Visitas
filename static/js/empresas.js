
setTimeout(function () {
  const mensagens = document.getElementById("mensagens");

  if (mensagens) {
    mensagens.classList.add("messages-hidden");
  }
}, 3000);


// ======================================================
// 2. NORMALIZAR TEXTO PARA PESQUISA
// ======================================================

function normalizarTexto(texto) {
  return texto
    .toLocaleLowerCase("pt-BR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "");
}

// ======================================================
// 3. ELEMENTOS DA PÁGINA
// ======================================================

const campoPesquisa = document.getElementById("pesquisa-empresa");
const cartoes = document.querySelectorAll("[data-company-card]");
const mensagemVazia = document.getElementById("nenhum-resultado");

// ======================================================
// 4. PESQUISAR EMPRESAS SEM RECARREGAR A PÁGINA
// ======================================================

campoPesquisa.addEventListener("input", function () {

  // Normaliza o que o usuário digitou.
  const termo = normalizarTexto(campoPesquisa.value);

  // Contabiliza quantas empresas correspondem à pesquisa.
  let encontrados = 0;

  // Percorre todos os cartões de empresas.
  cartoes.forEach(function (cartao) {

    // Obtém e normaliza todo o texto do cartão.
    const conteudo = normalizarTexto(cartao.textContent);

    // Verifica se o conteúdo contém o termo pesquisado.
    const corresponde = conteudo.includes(termo);

    // Oculta ou exibe o cartão.
    cartao.hidden = !corresponde;

    // Atualiza a quantidade de resultados.
    if (corresponde) {
      encontrados++;
    }

  });

  // Exibe a mensagem quando nenhuma empresa é encontrada.
  mensagemVazia.hidden = encontrados !== 0;

});