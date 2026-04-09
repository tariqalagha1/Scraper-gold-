import React from 'react';

const JsonPreview = ({ data }) => (
  <pre className="overflow-x-auto rounded-[28px] border border-[#4f453a]/50 bg-[rgba(8,11,14,0.78)] p-6 text-xs leading-6 text-[#ffd3a0] shadow-sm sm:text-sm">
    {JSON.stringify(data, null, 2)}
  </pre>
);

export default JsonPreview;
