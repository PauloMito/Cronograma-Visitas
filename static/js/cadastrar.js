
const possuiAssessoria =
  document.getElementById("possui_assessoria");

const campoAssessoria =
  document.getElementById("campo_assessoria");

const dataInicio =
  document.getElementById("data_inicio_assessoria");

const periodicidade =
  document.getElementById("periodicidade_assessoria");


// ========================================
// 1. CONTROLE DA ASSESSORIA
// ========================================

function atualizarAssessoria() {
  if (possuiAssessoria.checked) {
    campoAssessoria.style.display = "block";

    dataInicio.required = true;
    periodicidade.required = true;
  } else {
    campoAssessoria.style.display = "none";

    dataInicio.required = false;
    periodicidade.required = false;

    dataInicio.value = "";
    periodicidade.value = "";
  }
}

possuiAssessoria.addEventListener(
  "change",
  atualizarAssessoria
);

atualizarAssessoria();


// ========================================
// 2. CONTROLE DO TIPO DE INSCRIÇÃO
// ========================================

const tipoInscricao =
  document.getElementById("tipo_inscricao");

const numeroInscricao =
  document.getElementById("numero_inscricao");

const labelNumeroInscricao =
  document.getElementById("label_numero_inscricao");


function atualizarTipoInscricao() {
  const tipo = tipoInscricao.value;

  if (tipo === "CNPJ") {
    labelNumeroInscricao.textContent = "Número do CNPJ:";
    numeroInscricao.placeholder = "00.000.000/0000-00";
    numeroInscricao.maxLength = 18;
  } else {
    labelNumeroInscricao.textContent = "Número do CAEPF:";
    numeroInscricao.placeholder = "000.000.000/000-00";
    numeroInscricao.maxLength = 18;
  }

  numeroInscricao.value = formatarInscricao(
    numeroInscricao.value,
    tipo
  );
}

tipoInscricao.addEventListener(
  "change",
  atualizarTipoInscricao
);


// ========================================
// 3. FORMATAÇÃO DOS NÚMEROS
// ========================================

function formatarInscricao(valor, tipo) {
  let numeros = valor.replace(/\D/g, "");

  if (tipo === "CNPJ") {
    // CNPJ: 14 dígitos
    numeros = numeros.slice(0, 14);

    if (numeros.length > 12) {
      numeros = numeros.replace(
        /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{1,2})$/,
        "$1.$2.$3/$4-$5"
      );
    } else if (numeros.length > 8) {
      numeros = numeros.replace(
        /^(\d{2})(\d{3})(\d{3})(\d{1,4})$/,
        "$1.$2.$3/$4"
      );
    } else if (numeros.length > 5) {
      numeros = numeros.replace(
        /^(\d{2})(\d{3})(\d{1,3})$/,
        "$1.$2.$3"
      );
    } else if (numeros.length > 2) {
      numeros = numeros.replace(
        /^(\d{2})(\d{1,3})$/,
        "$1.$2"
      );
    }
  } else {
    // CAEPF: 14 dígitos
    numeros = numeros.slice(0, 14);

    if (numeros.length > 12) {
      numeros = numeros.replace(
        /^(\d{3})(\d{3})(\d{3})(\d{3})(\d{1,2})$/,
        "$1.$2.$3/$4-$5"
      );
    } else if (numeros.length > 9) {
      numeros = numeros.replace(
        /^(\d{3})(\d{3})(\d{3})(\d{1,3})$/,
        "$1.$2.$3/$4"
      );
    } else if (numeros.length > 6) {
      numeros = numeros.replace(
        /^(\d{3})(\d{3})(\d{1,3})$/,
        "$1.$2.$3"
      );
    } else if (numeros.length > 3) {
      numeros = numeros.replace(
        /^(\d{3})(\d{1,3})$/,
        "$1.$2"
      );
    }
  }

  return numeros;
}


// ========================================
// 4. FORMATAÇÃO DURANTE A DIGITAÇÃO
// ========================================

numeroInscricao.addEventListener("input", function () {
  numeroInscricao.value = formatarInscricao(
    numeroInscricao.value,
    tipoInscricao.value
  );
});


// ========================================
// 5. CONFIGURAÇÃO INICIAL
// ========================================

atualizarTipoInscricao();