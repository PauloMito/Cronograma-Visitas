
document.addEventListener("click", async function (evento) {

  // Identifica o botão clicado.
  const botao = evento.target.closest("[data-visita-botao]");

  if (!botao) {
    return;
  }

  // Localiza o cartão da empresa.
  const empresa = botao.closest("[data-visita-item]");

  if (!empresa) {
    return;
  }

  // Obtém os dados da visita.
  const empresaId = botao.dataset.empresaId;
  const dataVisita = botao.dataset.dataVisita;
  const url = botao.dataset.url;

  // Descobre a situação atual.
  const realizada = !empresa.classList.contains(
    "visita-realizada"
  );

  // Evita cliques repetidos durante a comunicação.
  botao.disabled = true;

  try {

    // Envia a alteração para o Flask.
    const resposta = await fetch(url, {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        empresa_id: empresaId,
        data_visita: dataVisita,
        realizada: realizada
      })
    });

    const resultado = await resposta.json();

    if (!resposta.ok || !resultado.sucesso) {
      throw new Error(
        resultado.mensagem || "Não foi possível salvar."
      );
    }

    // Atualiza a aparência somente após a confirmação do servidor.
    empresa.classList.toggle(
      "visita-realizada",
      resultado.realizada
    );

    const texto = botao.querySelector(
      "[data-visita-texto]"
    );

    const icone = botao.querySelector(
      "[data-visita-icone]"
    );

    const status = empresa.querySelector(
      "[data-visita-status]"
    );

    // Atualiza o botão.
    texto.textContent = resultado.realizada
      ? "Desfazer conclusão"
      : "Marcar visita realizada";

    icone.textContent = resultado.realizada
      ? "✓"
      : "○";

    botao.setAttribute(
      "aria-pressed",
      String(resultado.realizada)
    );

    // Atualiza o status.
    status.textContent = resultado.realizada
      ? "✓ Visita realizada"
      : "● Visita prevista";

    // Atualiza o contador.
    atualizarContador();

  } catch (erro) {

    console.error("Erro ao registrar visita:", erro);

    alert(
      "Não foi possível salvar a visita. Tente novamente."
    );

  } finally {

    // Libera o botão novamente.
    botao.disabled = false;
  }

});


function atualizarContador() {

  const contador = document.getElementById(
    "contador-realizadas"
  );

  if (!contador) {
    return;
  }

  const visitasRealizadas = document.querySelectorAll(
    "[data-visita-item].visita-realizada"
  ).length;

  contador.textContent = visitasRealizadas;
}