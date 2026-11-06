export interface CertificateFieldDefinition {
  readonly key: string;
  readonly label: string;
  readonly date?: boolean;
}

export interface CertificateFieldGroup {
  readonly title: string;
  readonly fields: readonly CertificateFieldDefinition[];
}

export const BIRTH_CERTIFICATE_GROUPS = [
  { title: 'Child', fields: [
    { key: 'birthCertificateChildSurname', label: 'Surname' },
    { key: 'birthCertificateChildGivenName', label: 'Given name' },
    { key: 'birthCertificateChildPatronymic', label: 'Patronymic' },
    { key: 'birthCertificateChildDateOfBirth', label: 'Date of birth', date: true },
    { key: 'birthCertificateChildPlaceOfBirth', label: 'Place of birth' },
  ] },
  { title: 'Father', fields: [
    { key: 'birthCertificateFatherSurname', label: 'Surname' },
    { key: 'birthCertificateFatherGivenName', label: 'Given name' },
    { key: 'birthCertificateFatherPatronymic', label: 'Patronymic' },
    { key: 'birthCertificateFatherDateOfBirth', label: 'Date of birth', date: true },
    { key: 'birthCertificateFatherCitizenship', label: 'Citizenship' },
    { key: 'birthCertificateFatherNationality', label: 'Nationality' },
  ] },
  { title: 'Mother', fields: [
    { key: 'birthCertificateMotherSurname', label: 'Surname' },
    { key: 'birthCertificateMotherGivenName', label: 'Given name' },
    { key: 'birthCertificateMotherPatronymic', label: 'Patronymic' },
    { key: 'birthCertificateMotherDateOfBirth', label: 'Date of birth', date: true },
    { key: 'birthCertificateMotherCitizenship', label: 'Citizenship' },
    { key: 'birthCertificateMotherNationality', label: 'Nationality' },
  ] },
  { title: 'Registration and issue', fields: [
    { key: 'birthCertificateRegistrationDate', label: 'Registration date', date: true },
    { key: 'birthCertificateRecordNumber', label: 'Record number' },
    { key: 'birthCertificateRegistryOffice', label: 'Registry office' },
    { key: 'birthCertificateIssueDate', label: 'Issue date', date: true },
    { key: 'birthCertificateSeries', label: 'Certificate series' },
    { key: 'birthCertificateNumber', label: 'Certificate number' },
  ] },
] as const satisfies readonly CertificateFieldGroup[];

export const MARRIAGE_CERTIFICATE_GROUPS = [
  { title: 'Spouse 1', fields: [
    { key: 'marriageCertificateSpouse1SurnameBefore', label: 'Surname before marriage' },
    { key: 'marriageCertificateSpouse1GivenNameBefore', label: 'Given name before marriage' },
    { key: 'marriageCertificateSpouse1PatronymicBefore', label: 'Patronymic before marriage' },
    { key: 'marriageCertificateSpouse1DateOfBirth', label: 'Date of birth', date: true },
    { key: 'marriageCertificateSpouse1PlaceOfBirth', label: 'Place of birth' },
    { key: 'marriageCertificateSpouse1Citizenship', label: 'Citizenship' },
    { key: 'marriageCertificateSpouse1Nationality', label: 'Nationality' },
    { key: 'marriageCertificateSpouse1SurnameAfter', label: 'Surname after marriage' },
  ] },
  { title: 'Spouse 2', fields: [
    { key: 'marriageCertificateSpouse2SurnameBefore', label: 'Surname before marriage' },
    { key: 'marriageCertificateSpouse2GivenNameBefore', label: 'Given name before marriage' },
    { key: 'marriageCertificateSpouse2PatronymicBefore', label: 'Patronymic before marriage' },
    { key: 'marriageCertificateSpouse2DateOfBirth', label: 'Date of birth', date: true },
    { key: 'marriageCertificateSpouse2PlaceOfBirth', label: 'Place of birth' },
    { key: 'marriageCertificateSpouse2Citizenship', label: 'Citizenship' },
    { key: 'marriageCertificateSpouse2Nationality', label: 'Nationality' },
    { key: 'marriageCertificateSpouse2SurnameAfter', label: 'Surname after marriage' },
  ] },
  { title: 'Registration and issue', fields: [
    { key: 'marriageCertificateMarriageDate', label: 'Marriage date', date: true },
    { key: 'marriageCertificateRecordDate', label: 'Record date', date: true },
    { key: 'marriageCertificateRecordNumber', label: 'Record number' },
    { key: 'marriageCertificateRegistryOffice', label: 'Registry office' },
    { key: 'marriageCertificateIssueDate', label: 'Issue date', date: true },
    { key: 'marriageCertificateSeries', label: 'Certificate series' },
    { key: 'marriageCertificateNumber', label: 'Certificate number' },
  ] },
] as const satisfies readonly CertificateFieldGroup[];

export type BirthCertificateField = (typeof BIRTH_CERTIFICATE_GROUPS)[number]['fields'][number]['key'];
export type MarriageCertificateField = (typeof MARRIAGE_CERTIFICATE_GROUPS)[number]['fields'][number]['key'];
export type CertificateField = BirthCertificateField | MarriageCertificateField;
export const BIRTH_CERTIFICATE_FIELDS = BIRTH_CERTIFICATE_GROUPS.flatMap<CertificateFieldDefinition & { key: BirthCertificateField }>((group) => [...group.fields]);
export const MARRIAGE_CERTIFICATE_FIELDS = MARRIAGE_CERTIFICATE_GROUPS.flatMap<CertificateFieldDefinition & { key: MarriageCertificateField }>((group) => [...group.fields]);
export const CERTIFICATE_FIELDS: readonly (CertificateFieldDefinition & { key: CertificateField })[] = [...BIRTH_CERTIFICATE_FIELDS, ...MARRIAGE_CERTIFICATE_FIELDS];
